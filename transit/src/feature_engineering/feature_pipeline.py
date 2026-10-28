"""Shared, versioned feature pipelines used identically at training and serving time (PRD 5.2 / 8.3).

Two pipeline kinds:
  * "leg"   - stop-to-stop travel time (Amazon legs); drives the routing cost matrix.
  * "order" - end-to-end delivery time (Food Delivery); observed-outcome model.
  * "legacy"- the original two-step pipeline (kept so old tests/notebooks keep working).

Leakage guard: `historical_delay_index` for a leg is the mean slowness ratio of the same station
over strictly earlier calendar dates, computed from a table fitted on training rows only.
"""
import datetime
import os
import pickle
import re

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from src.paths import MODELS_DIR

# Amazon station prefix -> UTC offset (hours, northern-summer DST) so hour/day features are station-local.
_UTC_OFFSET = {"DLA": -7, "DSE": -7, "DCH": -5, "DBO": -4, "DAU": -5}

_ZONE = re.compile(r"^([A-Z])-(\d+)\.(\d+)([A-Z])$")

LEG_FEATURES = [
    "station_code", "direct_km", "bearing_sin", "bearing_cos", "from_lat", "from_lng", "to_lat", "to_lng",
    "dlat", "dlng", "same_zone", "from_zone_major", "from_zone_minor", "to_zone_major", "to_zone_minor",
    "zone_major_diff", "zone_minor_diff", "to_zone_kind", "hour_sin", "hour_cos", "dow", "is_peak_hour",
    "stop_idx", "n_stops", "stop_frac", "to_n_packages", "to_volume_cm3", "to_n_time_windows",
    "from_service_sec", "capacity_cm3", "to_station_km", "historical_delay_index",
]
FOOD_FEATURES = [
    "distance_km", "weather", "traffic_level", "time_of_day", "vehicle_type", "prep_time_min", "courier_exp_yrs",
]


def haversine_km(lat1, lng1, lat2, lng2):
    lat1, lng1, lat2, lng2 = (np.radians(np.asarray(a, dtype=float)) for a in (lat1, lng1, lat2, lng2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _bearing(lat1, lng1, lat2, lng2):
    lat1, lat2, dl = np.radians(lat1), np.radians(lat2), np.radians(np.asarray(lng2) - np.asarray(lng1))
    y = np.sin(dl) * np.cos(lat2)
    x = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dl)
    return np.arctan2(y, x)


def _zone_parts(series: pd.Series):
    kind, major, minor = [], [], []
    for z in series.astype(str):
        m = _ZONE.match(z)
        if m:
            kind.append(m.group(1)); major.append(float(m.group(2))); minor.append(float(m.group(3)))
        else:
            kind.append("none"); major.append(np.nan); minor.append(np.nan)
    return pd.Series(kind, index=series.index), pd.Series(major, index=series.index), pd.Series(minor, index=series.index)


class LegFeatureBuilder(BaseEstimator, TransformerMixin):
    """Raw leg rows (see build_amazon_legs) -> model features. Stateful: holds the delay-history table."""

    def fit(self, X: pd.DataFrame, y=None):
        df = X.copy()
        km = haversine_km(df.from_lat, df.from_lng, df.to_lat, df.to_lng)
        y = np.asarray(y, dtype=float)
        spk = y / np.maximum(km, 0.05)
        self.global_sec_per_km_ = float(np.median(spk))
        ratio = spk / self.global_sec_per_km_
        date = pd.to_datetime(df["planned_depart_ts"]).dt.normalize()
        daily = pd.DataFrame({"station": df.station_code.values, "date": date.values, "r": ratio}).groupby(
            ["station", "date"]).r.agg(["sum", "count"]).reset_index()
        self.history_ = {}
        for st, g in daily.groupby("station"):
            g = g.sort_values("date")
            self.history_[st] = (g["date"].values, np.cumsum(g["sum"].values), np.cumsum(g["count"].values))
        self.is_fitted_ = True
        return self

    def _hdi(self, station: pd.Series, ts: pd.Series) -> np.ndarray:
        date = pd.to_datetime(ts).dt.normalize().values
        out = np.ones(len(station))
        for st in station.unique():
            if st not in self.history_:
                continue
            d, s, c = self.history_[st]
            mask = (station == st).values
            k = np.searchsorted(d, date[mask], side="left")  # number of history days strictly before the row's day
            vals = np.where(k > 0, s[np.maximum(k - 1, 0)] / np.maximum(c[np.maximum(k - 1, 0)], 1), 1.0)
            out[mask] = vals
        return out

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.reset_index(drop=True)
        ts_utc = pd.to_datetime(df["planned_depart_ts"])
        offset = df["station_code"].astype(str).str[:3].map(_UTC_OFFSET).fillna(-7)
        ts = ts_utc + pd.to_timedelta(offset, unit="h")  # station-local clock
        out = pd.DataFrame(index=df.index)
        out["station_code"] = df["station_code"].astype(str)
        out["direct_km"] = haversine_km(df.from_lat, df.from_lng, df.to_lat, df.to_lng)
        b = _bearing(df.from_lat.values, df.from_lng.values, df.to_lat.values, df.to_lng.values)
        out["bearing_sin"], out["bearing_cos"] = np.sin(b), np.cos(b)
        for c in ("from_lat", "from_lng", "to_lat", "to_lng"):
            out[c] = df[c].astype(float)
        out["dlat"], out["dlng"] = out.to_lat - out.from_lat, out.to_lng - out.from_lng
        fk, fmaj, fmin = _zone_parts(df["from_zone"])
        tk, tmaj, tmin = _zone_parts(df["to_zone"])
        out["same_zone"] = (df["from_zone"].astype(str) == df["to_zone"].astype(str)).astype(int)
        out["from_zone_major"], out["from_zone_minor"], out["to_zone_major"], out["to_zone_minor"] = fmaj, fmin, tmaj, tmin
        out["zone_major_diff"], out["zone_minor_diff"] = (tmaj - fmaj).abs(), (tmin - fmin).abs()
        out["to_zone_kind"] = tk
        hour = ts.dt.hour + ts.dt.minute / 60.0
        out["hour_sin"], out["hour_cos"] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
        out["dow"] = ts.dt.dayofweek
        out["is_peak_hour"] = (((hour >= 7) & (hour < 10)) | ((hour >= 16) & (hour < 20))).astype(int)
        out["stop_idx"], out["n_stops"] = df["stop_idx"], df["n_stops"]
        out["stop_frac"] = df["stop_idx"] / np.maximum(df["n_stops"], 1)
        for c in ("to_n_packages", "to_volume_cm3", "to_n_time_windows", "from_service_sec", "capacity_cm3", "to_station_km"):
            out[c] = df[c].astype(float)
        out["historical_delay_index"] = self._hdi(df["station_code"].astype(str), ts_utc)
        return out[LEG_FEATURES]


class FoodFeatureBuilder(BaseEstimator, TransformerMixin):
    """Canonical food-delivery rows -> model features (stateless)."""

    def fit(self, X, y=None):
        self.is_fitted_ = True
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        out = X.reset_index(drop=True)[FOOD_FEATURES].copy()
        for c in ("weather", "traffic_level", "time_of_day", "vehicle_type"):
            out[c] = out[c].astype(str)
        for c in ("distance_km", "prep_time_min", "courier_exp_yrs"):
            out[c] = out[c].astype(float)
        return out


class CategoricalEncoder(BaseEstimator, TransformerMixin):
    """Ordinal-encodes object/category columns (unknown -> -1); records which columns are categorical."""

    def __init__(self):
        self.encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        self.cat_cols = []

    @staticmethod
    def _clean(X: pd.DataFrame) -> pd.DataFrame:
        drop = ["order_id", "created_at", "source_dataset", "actual_delivery_time_minutes"]
        return X.drop(columns=[c for c in drop if c in X.columns], errors="ignore")

    def fit(self, X: pd.DataFrame, y=None):
        X = self._clean(X)
        self.cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
        if self.cat_cols:
            self.encoder.fit(X[self.cat_cols])
        self.is_fitted_ = True
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = self._clean(X).copy()
        cols = [c for c in self.cat_cols if c in X.columns]
        if cols:
            X[cols] = self.encoder.transform(X[cols])
        return X


class SpatialDistanceTransformer(BaseEstimator, TransformerMixin):
    """Legacy: planar distance in degrees (kept only for the legacy pipeline)."""

    def fit(self, X, y=None):
        self.is_fitted_ = True
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X_out = X.copy()
        if "pickup_lat" in X_out.columns and "delivery_lat" in X_out.columns:
            dx = X_out["pickup_lat"] - X_out["delivery_lat"]
            dy = X_out["pickup_lng"] - X_out["delivery_lng"]
            X_out["euclidean_distance"] = np.sqrt(dx ** 2 + dy ** 2)
        return X_out


def build_feature_pipeline(kind: str = "legacy") -> Pipeline:
    if kind == "leg":
        return Pipeline([("features", LegFeatureBuilder()), ("encoder", CategoricalEncoder())])
    if kind == "order":
        return Pipeline([("features", FoodFeatureBuilder()), ("encoder", CategoricalEncoder())])
    return Pipeline([("spatial", SpatialDistanceTransformer()), ("encoder", CategoricalEncoder())])


def save_pipeline(pipeline: Pipeline, output_dir: str = str(MODELS_DIR)) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"feature_pipeline_{timestamp}_unset.pkl")
    with open(filepath, "wb") as f:
        pickle.dump(pipeline, f)
    return filepath


def load_pipeline(filepath: str) -> Pipeline:
    with open(filepath, "rb") as f:
        return pickle.load(f)
