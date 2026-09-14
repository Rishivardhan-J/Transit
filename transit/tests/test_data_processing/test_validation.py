import pandas as pd
import pytest
from datetime import datetime
from src.data_processing.schemas import Order
from src.data_processing.processor import DataProcessor


def test_validation_catches_bad_coordinates():
    processor = DataProcessor()
    
    # Valid order except bad pickup_lat
    bad_data = pd.DataFrame([{
        'order_id': 'ORD1',
        'pickup_lat': 150.0, # invalid, > 90
        'pickup_lng': -122.0,
        'delivery_lat': 37.8,
        'delivery_lng': -122.5,
        'demand_weight': 10.0,
        'priority': 'standard',
        'time_window_start': datetime(2024, 1, 1, 8, 0, 0),
        'time_window_end': datetime(2024, 1, 1, 10, 0, 0),
        'service_time_minutes': 10.0,
        'created_at': datetime(2024, 1, 1, 7, 0, 0),
        'status': 'pending'
    }])
    
    report = processor.validate_batch(bad_data, Order)
    assert not report.is_valid()
    assert report.error_count > 0
    assert any('pickup_lat' in err.field for err in report.errors)


def test_validation_catches_bad_time_window():
    processor = DataProcessor()
    
    bad_data = pd.DataFrame([{
        'order_id': 'ORD2',
        'pickup_lat': 37.7,
        'pickup_lng': -122.0,
        'delivery_lat': 37.8,
        'delivery_lng': -122.5,
        'demand_weight': 10.0,
        'priority': 'standard',
        'time_window_start': datetime(2024, 1, 1, 10, 0, 0),
        'time_window_end': datetime(2024, 1, 1, 8, 0, 0), # end before start
        'service_time_minutes': 10.0,
        'created_at': datetime(2024, 1, 1, 7, 0, 0),
        'status': 'pending'
    }])
    
    report = processor.validate_batch(bad_data, Order)
    assert not report.is_valid()
    assert any('time_window_end' in err.message or 'time_window_start' in err.message for err in report.errors)


def test_duplicate_removal():
    processor = DataProcessor()
    data = pd.DataFrame([
        {'id': 1, 'val': 'a'},
        {'id': 1, 'val': 'a'},
        {'id': 2, 'val': 'b'}
    ])
    
    deduped = processor.remove_duplicates(data)
    assert len(deduped) == 2
