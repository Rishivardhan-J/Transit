"""Leakage and train/serve parity tests for the leg feature pipeline."""
import numpy as np
import pandas as pd
import pytest

from src.feature_engineering.feature_pipeline import LEG_FEATURES, build_feature_pipeline


def make_legs(days=6, per_day=40, seed=0, slow_from_day=3):
    rng = np.random.RandomState(seed)
    rows = []
    for d in range(days):
        for i in range(per_day):
            lat, lng = 34.05 + rng.uniform(-0.05, 0.05), -118.25 + rng.uniform(-0.05, 0.05)
            dlat, dlng = rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02)
            km = 111 * np.hypot(dlat, dlng * 0.83)
            rows.append({
                "route_id": f"r{d}", "station_code": "DLA3", "planned_depart_ts": pd.Timestamp("2018-07-20") + pd.Timedelta(days=d, hours=16),
                "stop_idx": i, "n_stops": per_day, "from_lat": lat, "from_lng": lng, "to_lat": lat + dlat, "to_lng": lng + dlng,
                "from_zone": "P-12.3C", "to_zone": "P-12.4B", "to_n_packages": 1, "to_volume_cm3": 1000.0, "to_n_time_windows": 0,
                "from_service_sec": 60.0, "capacity_cm3": 3e6, "to_station_km": 3.0,
                # from `slow_from_day` onward everything is 2x slower: a feature that peeks at the same day would leak it
                "travel_time_sec": km * 120 * (2.0 if d >= slow_from_day else 1.0),
            })
    return pd.DataFrame(rows)


def test_historical_delay_index_uses_only_strictly_earlier_days():
    df = make_legs()
    pipe = build_feature_pipeline("leg")
    X = pipe.fit_transform(df, df.travel_time_sec.values)
    day = pd.to_datetime(df.planned_depart_ts).dt.normalize()
    first = day.min()
    hdi = lambda k: X.loc[day == first + pd.Timedelta(days=k), "historical_delay_index"]
    # day 0 has no history -> neutral 1.0; days 1-3 only see fast days
    assert np.allclose(hdi(0), 1.0)
    fast = hdi(2).iloc[0]
    # day 3 is the first slow day (2x), yet its own slowness must be invisible to it
    assert hdi(3).max() == pytest.approx(fast, rel=0.01)
    # day 4 sees day 3's slowness (but not its own)
    assert hdi(4).iloc[0] > fast * 1.1
    assert hdi(4).iloc[0] < hdi(5).iloc[0]  # still climbing as more slow history accumulates


def test_features_do_not_depend_on_other_rows_in_the_batch():
    """Given a fitted pipeline, a row's features cannot change when later rows are added to the batch."""
    df = make_legs()
    pipe = build_feature_pipeline("leg")
    pipe.fit(df, df.travel_time_sec.values)
    cutoff = pd.Timestamp("2018-07-24")
    past = df[pd.to_datetime(df.planned_depart_ts) < cutoff]
    n = len(past)
    pd.testing.assert_frame_equal(pipe.transform(df).iloc[:n].reset_index(drop=True), pipe.transform(past).reset_index(drop=True))


def test_target_is_never_a_feature():
    df = make_legs()
    X = build_feature_pipeline("leg").fit_transform(df, df.travel_time_sec.values)
    assert "travel_time_sec" not in X.columns and "route_id" not in X.columns


def test_serving_row_matches_training_columns():
    df = make_legs()
    pipe = build_feature_pipeline("leg")
    X = pipe.fit_transform(df, df.travel_time_sec.values)
    single = pipe.transform(df.iloc[[7]])
    assert list(single.columns) == list(X.columns) == [c for c in LEG_FEATURES]
    pd.testing.assert_frame_equal(single.reset_index(drop=True), X.iloc[[7]].reset_index(drop=True))


def test_unknown_station_and_zone_are_handled():
    df = make_legs()
    pipe = build_feature_pipeline("leg")
    pipe.fit(df, df.travel_time_sec.values)
    odd = df.iloc[[0]].copy()
    odd["station_code"], odd["from_zone"], odd["to_zone"] = "XXX9", "none", "none"
    X = pipe.transform(odd)
    assert X["historical_delay_index"].iloc[0] == 1.0
    assert X["station_code"].iloc[0] == -1
