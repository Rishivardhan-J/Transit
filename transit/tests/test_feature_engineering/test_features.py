import pandas as pd
import pytest
from datetime import datetime, timedelta
from src.feature_engineering.features import calculate_historical_delay_index
from src.feature_engineering.feature_pipeline import build_feature_pipeline


def test_leakage_guard():
    # Current dataset (what we are predicting for)
    current_df = pd.DataFrame({
        'order_id': ['NEW1', 'NEW2']
    })
    
    as_of = datetime(2024, 6, 1, 12, 0, 0)
    
    # Historical dataset with one valid row and one leaky row
    historical_df = pd.DataFrame({
        'order_id': ['OLD1', 'LEAKY1'],
        'created_at': [
            datetime(2024, 6, 1, 10, 0, 0), # Valid, before as_of
            datetime(2024, 6, 1, 13, 0, 0)  # Leaky, after as_of
        ],
        'delay_minutes': [5.0, 100.0]
    })
    
    # The delay should only average the valid row (5.0), not the leaky one
    result = calculate_historical_delay_index(current_df, historical_df, as_of)
    assert result.iloc[0] == 5.0
    assert result.iloc[1] == 5.0


def test_pipeline_determinism():
    pipeline = build_feature_pipeline()
    
    df = pd.DataFrame({
        'pickup_lat': [37.7749],
        'pickup_lng': [-122.4194],
        'delivery_lat': [34.0522],
        'delivery_lng': [-118.2437],
        'time_window_start': ['2024-06-01 08:00:00'],
        'time_window_end': ['2024-06-01 10:00:00']
    })
    
    res1 = pipeline.fit_transform(df)
    res2 = pipeline.transform(df)
    
    # Check that transform produces identical results to fit_transform for the same input
    pd.testing.assert_frame_equal(res1, res2)
    
    # Check that expected features are there
    assert 'direct_distance_km' in res1.columns
    assert 'is_peak_hour' in res1.columns
