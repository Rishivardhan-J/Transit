"""Inference on top of a model bundle: calibrated quantiles, plain-language SHAP, batch leg matrices."""
from functools import lru_cache
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import shap

from src.models.model_registry import Bundle, load_bundle

# Plain-language templates for the explanation panel (feature -> how to word its value).
_LABELS = {
    "direct_km": ("straight-line distance", "{:.2f} km"),
    "distance_km": ("delivery distance", "{:.1f} km"),
    "historical_delay_index": ("recent station slowness", "{:.2f}x normal"),
    "traffic_level": ("traffic level", None), "weather": ("weather", None), "time_of_day": ("time of day", None),
    "prep_time_min": ("preparation time", "{:.0f} min"), "courier_exp_yrs": ("courier experience", "{:.1f} yrs"),
    "to_station_km": ("distance of the stop from the depot", "{:.1f} km"),
    "stop_frac": ("position in the route", "{:.0%} of the way through"),
    "is_peak_hour": ("peak hour", None), "same_zone": ("same delivery zone", None),
}


@lru_cache(maxsize=4)
def get_bundle(kind: str, version: str = "latest") -> Bundle:
    return load_bundle(kind, version)


def clear_cache() -> None:
    get_bundle.cache_clear()


def features_for(bundle: Bundle, raw: pd.DataFrame) -> pd.DataFrame:
    X = bundle.pipeline.transform(raw)
    return X[bundle.metadata["features"]]


def predict_quantiles(bundle: Bundle, raw: pd.DataFrame) -> pd.DataFrame:
    """Calibrated p10/p50/p90 in the bundle's native unit (sec for legs, min for orders).
    p10/p90 carry the conformal offset fitted on validation data; ordering is p10 <= p50 <= p90 by construction."""
    X = features_for(bundle, raw)
    q = bundle.metadata["metrics"]["cqr_offset"]
    p50 = np.maximum(bundle.models["p50"].predict(X), 0.0)
    p10 = np.maximum(np.minimum(bundle.models["p10"].predict(X) - q, p50), 0.0)
    p90 = np.maximum(bundle.models["p90"].predict(X) + q, p50)
    return pd.DataFrame({"p10": p10, "p50": p50, "p90": p90}, index=raw.index)


def _describe(feature: str, value, raw_value) -> str:
    label, fmt = _LABELS.get(feature, (feature.replace("_", " "), None))
    shown = raw_value if raw_value is not None else value
    if fmt and isinstance(value, (int, float)) and not (isinstance(value, float) and np.isnan(value)):
        return f"{label} {fmt.format(value)}"
    return f"{label}: {shown}"


def explain(bundle: Bundle, raw: pd.DataFrame, top_k: int = 5) -> List[List[Dict]]:
    """Per-row top SHAP contributions of the p50 model, in the model's unit, with a readable `text`."""
    X = features_for(bundle, raw)
    sv = shap.TreeExplainer(bundle.models["p50"]).shap_values(X)
    enc = bundle.pipeline.named_steps["encoder"]
    out = []
    for i in range(len(X)):
        order = np.argsort(-np.abs(sv[i]))[:top_k]
        row = []
        for j in order:
            name = X.columns[j]
            val = X.iloc[i, j]
            raw_val = None
            if name in enc.cat_cols:
                k = enc.cat_cols.index(name)
                cats = enc.encoder.categories_[k]
                raw_val = cats[int(val)] if 0 <= int(val) < len(cats) else "unknown"
            v = float(val) if not name in enc.cat_cols else str(raw_val)
            row.append({"feature": name, "value": v, "impact": round(float(sv[i, j]), 3),
                        "unit": bundle.metadata["unit"], "text": _describe(name, v, raw_val)})
        out.append(row)
    return out
