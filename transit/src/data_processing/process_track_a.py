import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def process_food_delivery():
    """
    Processes the Kaggle Food Delivery dataset into the uniform Prediction schema.
    Since the raw data lacks coordinates and dates, we synthesize them to match 
    the schema requirements, preserving the empirical Distance_km and Delivery_Time_min.
    """
    raw_path = "transit/data/raw/food_delivery/Food_Delivery_Times.csv"
    out_path = "transit/data/processed/food_delivery.parquet"
    
    if not os.path.exists(raw_path):
        print(f"Skipping food_delivery, raw file not found: {raw_path}")
        return
        
    df = pd.read_csv(raw_path)
    
    # Clean column names
    df.columns = [c.strip() for c in df.columns]
    
    # 1. Synthesize timestamps (chronological sequence over a month)
    # We'll spread the 1000 rows over June 2024
    start_date = datetime(2024, 6, 1, 8, 0, 0)
    timestamps = [start_date + timedelta(hours=i*0.5) for i in range(len(df))]
    df['created_at'] = timestamps
    
    # 2. Synthesize coordinates to match empirical Distance_km
    # 1 deg latitude is ~111km. We'll set pickup at origin, dropoff along Y axis.
    df['pickup_lat'] = 37.7749 # SF approx
    df['pickup_lng'] = -122.4194
    df['delivery_lat'] = df['pickup_lat'] + (df['Distance_km'] / 111.0)
    df['delivery_lng'] = df['pickup_lng']
    
    # 3. Map to schema
    df = df.rename(columns={
        'Order_ID': 'order_id',
        'Vehicle_Type': 'vehicle_type',
        'Delivery_Time_min': 'actual_delivery_time_minutes',
        'Weather': 'weather_severity',
        'Traffic_Level': 'traffic_score'
    })
    
    df['priority'] = 'standard'
    df['status'] = 'delivered'
    
    # Convert traffic to numerical score (Low=0.2, Medium=0.5, High=0.8)
    traffic_map = {'Low': 0.2, 'Medium': 0.5, 'High': 0.8}
    df['traffic_score'] = df['traffic_score'].map(traffic_map).fillna(0.5)
    
    final_cols = [
        'order_id', 'created_at', 'pickup_lat', 'pickup_lng', 'delivery_lat', 'delivery_lng',
        'vehicle_type', 'priority', 'status', 'weather_severity', 'traffic_score', 'actual_delivery_time_minutes'
    ]
    df_out = df[final_cols]
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df_out.to_parquet(out_path, index=False)
    print(f"Saved processed data to {out_path}")

if __name__ == "__main__":
    process_food_delivery()
