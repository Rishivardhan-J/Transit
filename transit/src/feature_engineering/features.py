import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional


def haversine_distance(lat1: pd.Series, lon1: pd.Series, lat2: pd.Series, lon2: pd.Series) -> pd.Series:
    """Calculate the great circle distance in kilometers between two points on the earth."""
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r


def compute_distance_features(df: pd.DataFrame) -> pd.DataFrame:
    """Computes direct distance between pickup and delivery."""
    df['direct_distance_km'] = haversine_distance(
        df['pickup_lat'], df['pickup_lng'], 
        df['delivery_lat'], df['delivery_lng']
    )
    return df


def compute_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Computes temporal features like peak hour indicator and urgency."""
    # Peak hours: 7-9 AM, 4-7 PM
    hour = df['time_window_start'].dt.hour
    is_peak_am = (hour >= 7) & (hour <= 9)
    is_peak_pm = (hour >= 16) & (hour <= 19)
    df['is_peak_hour'] = (is_peak_am | is_peak_pm).astype(int)
    
    # Urgency: time window duration in minutes
    df['time_window_duration_min'] = (df['time_window_end'] - df['time_window_start']).dt.total_seconds() / 60.0
    return df


def calculate_historical_delay_index(
    current_df: pd.DataFrame, 
    historical_df: pd.DataFrame, 
    as_of_timestamp: datetime
) -> pd.Series:
    """
    Calculates average delay in the historical dataset, ensuring NO LEAKAGE
    by filtering historical_df strictly before `as_of_timestamp`.
    """
    # LEAKAGE GUARD: strict cutoff
    valid_historical = historical_df[historical_df['created_at'] < as_of_timestamp]
    
    if len(valid_historical) != len(historical_df):
        leaked_rows = len(historical_df) - len(valid_historical)
        # We don't raise here, we just silently filter to enforce the guard.
        # But in a real test, if valid_historical is used, it won't contain future data.
        pass

    # Example computation: say historical_df has a 'delay_minutes' column
    # We might average it by some categorical area or hour.
    # For simplicity, if 'delay_minutes' doesn't exist, we mock a safe aggregate.
    if 'delay_minutes' in valid_historical.columns:
        avg_delay = valid_historical['delay_minutes'].mean()
    else:
        avg_delay = 0.0
        
    if pd.isna(avg_delay):
        avg_delay = 0.0

    return pd.Series(avg_delay, index=current_df.index)


def compute_route_efficiency(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes ratio of actual driven distance to direct distance (if actual exists),
    or sets a baseline.
    """
    if 'actual_distance_km' in df.columns and 'direct_distance_km' in df.columns:
        # Avoid division by zero
        df['route_efficiency'] = df['direct_distance_km'] / df['actual_distance_km'].clip(lower=0.1)
    return df


def compute_vehicle_utilization(df: pd.DataFrame, vehicle_capacity: float) -> pd.DataFrame:
    """
    Computes utilization ratio.
    """
    if 'demand_weight' in df.columns:
        df['vehicle_utilization'] = df['demand_weight'] / vehicle_capacity
    return df
