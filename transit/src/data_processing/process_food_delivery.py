"""Canonical Food Delivery dataset: the one Track A source with observed delivery outcomes and
real traffic/weather/time-of-day fields. All source columns are kept (the old pipeline dropped most)."""
from datetime import datetime, timedelta

import pandas as pd

from src.paths import PROCESSED_DIR, RAW_DIR

OUT = PROCESSED_DIR / "food_model.parquet"
TARGET = "actual_delivery_time_minutes"


def build() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "food_delivery" / "Food_Delivery_Times.csv")
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={
        "Order_ID": "order_id", "Distance_km": "distance_km", "Weather": "weather",
        "Traffic_Level": "traffic_level", "Time_of_Day": "time_of_day", "Vehicle_Type": "vehicle_type",
        "Preparation_Time_min": "prep_time_min", "Courier_Experience_yrs": "courier_exp_yrs",
        "Delivery_Time_min": TARGET,
    })
    # The source has no timestamp; rows are taken in file order, half an hour apart (documented synthetic axis).
    start = datetime(2024, 6, 1, 8, 0, 0)
    df["created_at"] = [start + timedelta(minutes=30 * i) for i in range(len(df))]
    df["order_id"] = df["order_id"].astype(str)
    for c in ("weather", "traffic_level", "time_of_day", "vehicle_type"):
        df[c] = df[c].fillna("unknown").astype(str)
    df["courier_exp_yrs"] = df["courier_exp_yrs"].fillna(df["courier_exp_yrs"].median())
    df["prep_time_min"] = df["prep_time_min"].fillna(df["prep_time_min"].median())
    return df.dropna(subset=["distance_km", TARGET])


if __name__ == "__main__":
    d = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"Saved {len(d)} rows -> {OUT}")
    print(d.describe(include="all").T[["count", "unique", "mean"]])
