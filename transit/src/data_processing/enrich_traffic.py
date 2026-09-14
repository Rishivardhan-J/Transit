import pandas as pd
import numpy as np

# TRAFFIC_PROVIDER = SYNTHETIC_OSRM
# Based on user selection, we are using the synthetic path.
# Paid paths (TOMTOM, HERE) are stubbed below.

def enrich_traffic_synthetic(df: pd.DataFrame, time_col: str = 'time_window_start') -> pd.DataFrame:
    """
    Generates synthetic traffic multipliers based on time-of-day.
    Assumes standard rush hours: 7-9 AM, 4-7 PM.
    """
    df_enriched = df.copy()
    
    if time_col not in df_enriched.columns:
        df_enriched['traffic_score'] = 1.0 # Default multiplier
        return df_enriched
        
    df_enriched[time_col] = pd.to_datetime(df_enriched[time_col])
    hour = df_enriched[time_col].dt.hour
    
    # Base traffic multiplier
    multipliers = np.ones(len(df_enriched))
    
    # AM Peak (7-9)
    am_peak = (hour >= 7) & (hour <= 9)
    multipliers[am_peak] = 1.4
    
    # PM Peak (16-19)
    pm_peak = (hour >= 16) & (hour <= 19)
    multipliers[pm_peak] = 1.6
    
    # Late night (0-5)
    late_night = (hour >= 0) & (hour <= 5)
    multipliers[late_night] = 0.8
    
    # Add some random noise for realism (± 10%)
    noise = np.random.uniform(0.9, 1.1, len(df_enriched))
    
    df_enriched['traffic_score'] = multipliers * noise
    return df_enriched


def enrich_traffic_tomtom(df: pd.DataFrame) -> pd.DataFrame:
    """Stub for TomTom integration."""
    raise NotImplementedError("TomTom traffic enrichment not implemented yet.")


def enrich_traffic_here(df: pd.DataFrame) -> pd.DataFrame:
    """Stub for HERE integration."""
    raise NotImplementedError("HERE traffic enrichment not implemented yet.")


def enrich_traffic(df: pd.DataFrame, time_col: str = 'time_window_start') -> pd.DataFrame:
    """Main entry point for traffic enrichment."""
    # Since TRAFFIC_PROVIDER = SYNTHETIC_OSRM, we route directly to synthetic
    return enrich_traffic_synthetic(df, time_col)
