from functools import lru_cache

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends

from backend.models_db.user import Role, User
from backend.security.rbac import require_role
from src.models.model_registry import load_bundle
from src.paths import PROCESSED_DIR

router = APIRouter()

DATASETS = {
    "legs": {"path": "amazon_legs.parquet", "title": "Amazon last-mile legs", "target": "travel_time_sec",
             "numeric": ["travel_time_sec", "direct_km", "stop_idx", "to_n_packages", "to_station_km"], "sample": 150_000},
    "food": {"path": "food_model.parquet", "title": "Food delivery orders", "target": "actual_delivery_time_minutes",
             "numeric": ["actual_delivery_time_minutes", "distance_km", "prep_time_min", "courier_exp_yrs"], "sample": None},
}


def _hist(s: pd.Series, bins: int = 20):
    s = s.dropna()
    lo, hi = s.quantile(0.005), s.quantile(0.995)  # trim extreme tails so the bars are readable
    counts, edges = np.histogram(s.clip(lo, hi), bins=bins, range=(float(lo), float(hi)) if hi > lo else None)
    return [{"bin": f"{edges[i]:.3g}", "lo": float(edges[i]), "hi": float(edges[i + 1]), "count": int(c)} for i, c in enumerate(counts)]


def _box(s: pd.Series):
    s = s.dropna()
    q1, med, q3 = s.quantile([0.25, 0.5, 0.75])
    iqr = q3 - q1
    lo_f, hi_f = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    inside = s[(s >= lo_f) & (s <= hi_f)]
    return {"min": float(inside.min()), "q1": float(q1), "median": float(med), "q3": float(q3), "max": float(inside.max()),
            "outliers": int(((s < lo_f) | (s > hi_f)).sum()), "n": int(len(s))}


@lru_cache(maxsize=4)
def _summarize(key: str):
    spec = DATASETS[key]
    path = PROCESSED_DIR / spec["path"]
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    if key == "legs":
        from src.feature_engineering.feature_pipeline import haversine_km
        df["direct_km"] = haversine_km(df.from_lat, df.from_lng, df.to_lat, df.to_lng)
    if spec["sample"] and len(df) > spec["sample"]:
        df = df.sample(spec["sample"], random_state=42)
    num = [c for c in spec["numeric"] if c in df.columns]
    corr = df[num].corr(numeric_only=True)
    out = {
        "title": spec["title"], "rows": int(len(df)), "target": spec["target"],
        "distributions": {c: _hist(df[c]) for c in num}, "boxplots": {c: _box(df[c]) for c in num},
        "correlation": [{"x": a, "y": b, "value": round(float(corr.loc[a, b]), 3)} for a in num for b in num],
        "categories": {c: [{"category": str(k), "count": int(v)} for k, v in df[c].value_counts().head(12).items()]
                       for c in ("traffic_level", "weather", "vehicle_type", "station_code") if c in df.columns},
    }
    if key == "legs":
        hour = pd.to_datetime(df["planned_depart_ts"]).dt.hour
        out["traffic_vs_time"] = [{"hour": int(h), "median": float(v)} for h, v in df.groupby(hour)["travel_time_sec"].median().items()]
    elif "traffic_level" in df.columns:
        order = ["Low", "Medium", "High"]
        g = df.groupby("traffic_level")[spec["target"]].median()
        out["traffic_vs_time"] = [{"traffic": t, "median": float(g[t])} for t in order if t in g.index]
    return out


@router.get("/summary")
def get_eda_summary(dataset: str = "food", current_user: User = Depends(require_role(Role.researcher))):
    """Real distributions, box plots, correlations and importances computed from the processed datasets."""
    if dataset not in DATASETS:
        dataset = "food"
    summary = _summarize(dataset)
    importance = None
    try:
        b = load_bundle("leg" if dataset == "legs" else "order")
        importance = {"version": b.version, "spearman": b.importance.get("impurity_vs_permutation_spearman"),
                      "features": b.importance.get("features", [])[:15]}
    except FileNotFoundError:
        pass
    return {"available": list(DATASETS), "dataset": dataset, "summary": summary, "importance": importance}
