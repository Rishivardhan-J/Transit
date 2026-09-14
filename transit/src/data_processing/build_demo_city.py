import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging

from src.data_processing.enrich_weather import enrich_weather
from src.data_processing.enrich_traffic import enrich_traffic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = Path("transit/data/processed")

def build_demo_city():
    """
    Builds the bridging dataset (Demo City).
    Uses synthetic geography + synthetic weather/traffic.
    Ensures schema matches Order Pydantic model structure where applicable.
    """
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("Building Demo City dataset...")
    
    # 1. Generate Synthetic Geography (using bounding box of a real city or just arbitrary)
    # Let's say San Francisco roughly
    sf_lat_min, sf_lat_max = 37.7, 37.8
    sf_lng_min, sf_lng_max = -122.5, -122.4
    
    n_records = 5000
    
    pickup_lats = np.random.uniform(sf_lat_min, sf_lat_max, n_records)
    pickup_lngs = np.random.uniform(sf_lng_min, sf_lng_max, n_records)
    delivery_lats = np.random.uniform(sf_lat_min, sf_lat_max, n_records)
    delivery_lngs = np.random.uniform(sf_lng_min, sf_lng_max, n_records)
    
    # 2. Time windows (spread over a few days)
    base_time = datetime(2024, 6, 1, 8, 0, 0)
    time_offsets = np.random.randint(0, 1440 * 7, n_records) # 7 days in minutes
    start_times = [base_time + timedelta(minutes=int(t)) for t in time_offsets]
    
    # duration between 30 and 120 mins
    durations = np.random.randint(30, 120, n_records)
    end_times = [st + timedelta(minutes=int(d)) for st, d in zip(start_times, durations)]
    
    # 3. Create DataFrame
    df = pd.DataFrame({
        'order_id': [f"ORD_{i:06d}" for i in range(n_records)],
        'pickup_lat': pickup_lats,
        'pickup_lng': pickup_lngs,
        'delivery_lat': delivery_lats,
        'delivery_lng': delivery_lngs,
        'demand_weight': np.random.uniform(1.0, 25.0, n_records).round(1),
        'priority': np.random.choice(['low', 'standard', 'high', 'urgent'], n_records, p=[0.1, 0.7, 0.15, 0.05]),
        'time_window_start': start_times,
        'time_window_end': end_times,
        'service_time_minutes': np.random.uniform(5.0, 15.0, n_records).round(1),
        'created_at': [st - timedelta(hours=np.random.randint(1, 24)) for st in start_times],
        'status': 'delivered'
    })
    
    # 4. Enrich
    logger.info("Enriching with traffic...")
    df = enrich_traffic(df, time_col='time_window_start')
    
    logger.info("Enriching with weather...")
    # NOTE: Since this is synthetic dates in the future or arbitrary, 
    # meteostat might return empty if it's strictly historical. 
    # For a real bridging dataset, we'd pull from historical track A.
    # We will call it, but if it returns NaNs, we fallback.
    df = enrich_weather(df, date_col='time_window_start')
    
    # Fill weather NaNs for synthetic demo if Meteostat fails
    if df['weather_severity'].isnull().all():
        logger.info("Applying synthetic weather fallback...")
        df['weather_severity'] = np.random.uniform(1.0, 2.0, n_records)
    
    # 5. Save
    output_path = PROCESSED_DATA_DIR / "demo_city.parquet"
    df.to_parquet(output_path, index=False)
    logger.info(f"Demo City dataset saved to {output_path}")

if __name__ == "__main__":
    build_demo_city()
