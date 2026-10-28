import numpy as np
import pandas as pd

from src.models.data_split import split_by_time
from src.models.train import conformal_offset


def test_split_by_time_is_grouped_and_ordered():
    days = pd.date_range("2024-01-01", periods=20)
    df = pd.DataFrame({"route_date": np.repeat(days, 50), "x": range(1000)})
    tr, va, te = split_by_time(df, "route_date")
    assert tr.route_date.max() < va.route_date.min() <= va.route_date.max() < te.route_date.min()
    assert len(tr) + len(va) + len(te) == len(df)
    assert set(tr.route_date).isdisjoint(va.route_date) and set(va.route_date).isdisjoint(te.route_date)


def test_conformal_offset_restores_target_coverage():
    rng = np.random.RandomState(0)
    n = 4000
    y = rng.normal(0, 1, 2 * n)
    # deliberately over-confident interval (true central 80% would be +-1.28)
    lo, hi = np.full(2 * n, -0.6), np.full(2 * n, 0.6)
    q = conformal_offset(y[:n], lo[:n], hi[:n], alpha=0.2)
    cov_before = np.mean((y[n:] >= lo[n:]) & (y[n:] <= hi[n:]))
    cov_after = np.mean((y[n:] >= lo[n:] - q) & (y[n:] <= hi[n:] + q))
    assert q > 0 and cov_before < 0.6
    assert abs(cov_after - 0.8) < 0.03
