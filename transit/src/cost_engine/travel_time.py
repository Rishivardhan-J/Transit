"""Travel-time providers: turn a distance matrix into a travel-time matrix (minutes).

The optimizer only ever sees a minutes matrix, so swapping providers (benchmark
Euclidean, speed profile, ML leg model) never touches solver code.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

import numpy as np


class TravelTimeProvider(ABC):
    @abstractmethod
    def matrix(self, coords: List[Tuple[float, float]], dist: np.ndarray,
               depart_hour: float = 12.0) -> np.ndarray:
        """Return an NxN matrix of travel minutes (zero diagonal)."""


class EuclideanTime(TravelTimeProvider):
    """Solomon convention: 1 distance unit == 1 minute."""

    def matrix(self, coords, dist, depart_hour: float = 12.0) -> np.ndarray:
        return np.array(dist, dtype=float)


class SpeedProfileTime(TravelTimeProvider):
    """distance / speed(hour). Fallback when no ML model is available."""

    def __init__(self, base_speed_kmh: float = 35.0, peak_slowdown: float = 0.6):
        self.base_speed_kmh = base_speed_kmh
        self.peak_slowdown = peak_slowdown

    def speed_kmh(self, hour: float) -> float:
        peak = 7 <= hour < 10 or 16 <= hour < 20
        return self.base_speed_kmh * (self.peak_slowdown if peak else 1.0)

    def matrix(self, coords, dist, depart_hour: float = 12.0) -> np.ndarray:
        return np.asarray(dist, dtype=float) / self.speed_kmh(depart_hour) * 60.0


class MLTravelTime(TravelTimeProvider):
    """Travel minutes from the leg quantile model: p50 + risk_lambda * (p90 - p50).

    risk_lambda=0 plans on the median; 1 plans on the calibrated p90 (cautious ETAs). All N*(N-1)
    legs are scored in one vectorised call. Route-context features the matrix cannot know
    (position in route, package counts...) use the training-set medians stored with the bundle.
    """

    def __init__(self, station_code: str = "DLA3", risk_lambda: float = 0.0, bundle=None):
        self.station_code = station_code
        self.risk_lambda = risk_lambda
        self._bundle = bundle

    @property
    def bundle(self):
        if self._bundle is None:
            from src.models.serving import get_bundle
            self._bundle = get_bundle("leg")
        return self._bundle

    def quantile_matrices(self, coords, depart_hour: float = 12.0):
        """Return {'p10','p50','p90'} NxN matrices in minutes."""
        import pandas as pd
        from src.feature_engineering.feature_pipeline import haversine_km
        from src.models.serving import predict_quantiles

        n = len(coords)
        c = np.asarray(coords, dtype=float)
        ii, jj = np.where(~np.eye(n, dtype=bool))
        d = self.bundle.metadata["defaults"]
        day = pd.Timestamp(self.bundle.metadata["time_ranges"]["test"][1]).normalize()
        offset = {"DLA": -7, "DSE": -7, "DCH": -5, "DBO": -4, "DAU": -5}.get(self.station_code[:3], -7)
        ts = day + pd.Timedelta(hours=depart_hour - offset)  # model features use station-local time
        raw = pd.DataFrame({
            "station_code": self.station_code, "planned_depart_ts": ts,
            "from_lat": c[ii, 0], "from_lng": c[ii, 1], "to_lat": c[jj, 0], "to_lng": c[jj, 1],
            "from_zone": "none", "to_zone": "none",
            "to_station_km": haversine_km(c[jj, 0], c[jj, 1], c[0, 0], c[0, 1]),
            **{k: v for k, v in d.items()},
        })
        q = predict_quantiles(self.bundle, raw)
        scale = 1.0 / 60.0 if self.bundle.metadata["unit"] == "sec" else 1.0
        out = {}
        for k in ("p10", "p50", "p90"):
            m = np.zeros((n, n))
            m[ii, jj] = q[k].values * scale
            out[k] = m
        return out

    def matrix(self, coords, dist, depart_hour: float = 12.0) -> np.ndarray:
        q = self.quantile_matrices(coords, depart_hour)
        return q["p50"] + self.risk_lambda * (q["p90"] - q["p50"])
