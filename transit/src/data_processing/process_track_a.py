import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta

def process_food_delivery():
    raw_path = "transit/data/raw/food_delivery/Food_Delivery_Times.csv"
    if not os.path.exists(raw_path):
        return pd.DataFrame()
        
    df = pd.read_csv(raw_path)
    df.columns = [c.strip() for c in df.columns]
    
    start_date = datetime(2024, 6, 1, 8, 0, 0)
    df['created_at'] = [start_date + timedelta(hours=i*0.5) for i in range(len(df))]
    
    df['pickup_lat'] = 37.7749
    df['pickup_lng'] = -122.4194
    df['delivery_lat'] = df['pickup_lat'] + (df['Distance_km'] / 111.0)
    df['delivery_lng'] = df['pickup_lng']
    
    df = df.rename(columns={
        'Order_ID': 'order_id',
        'Vehicle_Type': 'vehicle_type',
        'Delivery_Time_min': 'actual_delivery_time_minutes',
        'Weather': 'weather_severity',
        'Traffic_Level': 'traffic_score'
    })
    
    df['priority'] = 'standard'
    df['status'] = 'delivered'
    df['source_dataset'] = 'food_delivery'
    
    traffic_map = {'Low': 0.2, 'Medium': 0.5, 'High': 0.8}
    df['traffic_score'] = df['traffic_score'].map(traffic_map).fillna(0.5)
    
    return df

def process_mini_ecommerce():
    raw_path = "transit/data/raw/mini_ecommerce/Logistics_data_kaggle .csv"
    if not os.path.exists(raw_path):
        return pd.DataFrame()
        
    df = pd.read_csv(raw_path)
    df.columns = [c.strip() for c in df.columns]
    
    df['order_id'] = 'ME_' + df['order_id'].astype(str)
    df['created_at'] = pd.to_datetime(df['order_date'])
    df['actual_delivery_time_minutes'] = df['delivery_time_days'] * 24 * 60.0
    
    df['pickup_lat'] = 40.7128 # NY approx
    df['pickup_lng'] = -74.0060
    # Simulate delivery location based on warehouse and delivery time
    df['delivery_lat'] = df['pickup_lat'] + np.random.normal(0, 0.1, len(df))
    df['delivery_lng'] = df['pickup_lng'] + np.random.normal(0, 0.1, len(df))
    
    df['vehicle_type'] = 'van'
    df['priority'] = 'standard'
    df['status'] = 'delivered'
    df['weather_severity'] = 'Clear'
    df['traffic_score'] = 0.5
    df['source_dataset'] = 'mini_ecommerce'
    
    return df

def process_nyc_taxi():
    raw_path = "transit/data/raw/nyc_taxi/train.csv"
    if not os.path.exists(raw_path):
        return pd.DataFrame()
        
    df = pd.read_csv(raw_path, nrows=5000) # Sample 5k for speed
    
    df['order_id'] = 'NYC_' + df['id']
    df['created_at'] = pd.to_datetime(df['pickup_datetime'])
    df['actual_delivery_time_minutes'] = df['trip_duration'] / 60.0
    
    df['pickup_lat'] = df['pickup_latitude']
    df['pickup_lng'] = df['pickup_longitude']
    df['delivery_lat'] = df['dropoff_latitude']
    df['delivery_lng'] = df['dropoff_longitude']
    
    df['vehicle_type'] = 'car'
    df['priority'] = 'high' # Taxi is generally direct
    df['status'] = 'delivered'
    df['weather_severity'] = 'Clear'
    df['traffic_score'] = 0.6
    df['source_dataset'] = 'nyc_taxi'
    
    return df

def process_amazon_last_mile():
    base_dir = "transit/data/raw/amazon_last_mile"
    route_file = os.path.join(base_dir, "route_data.json")
    if not os.path.exists(route_file):
        return pd.DataFrame()
        
    with open(route_file, 'r') as f:
        route_data = json.load(f)
        
    rows = []
    # Sample up to 500 routes
    for i, (route_id, data) in enumerate(route_data.items()):
        # Create a proxy for travel time using stops
        num_stops = len(data['stops'])
        start_time = data['date_YYYY_MM_DD'] + " " + data['departure_time_utc']
        rows.append({
            'order_id': 'AMZN_' + route_id,
            'created_at': pd.to_datetime(start_time),
            'actual_delivery_time_minutes': num_stops * 3.5, # synthetic approximation
            'pickup_lat': 47.6062, # Seattle
            'pickup_lng': -122.3321,
            'delivery_lat': 47.6062 + np.random.normal(0, 0.05),
            'delivery_lng': -122.3321 + np.random.normal(0, 0.05),
            'vehicle_type': 'van',
            'priority': 'standard',
            'status': 'delivered',
            'weather_severity': 'Clear',
            'traffic_score': 0.5,
            'source_dataset': 'amazon_last_mile'
        })
    return pd.DataFrame(rows)

def combine_track_a():
    dfs = []
    
    food = process_food_delivery()
    if not food.empty:
        print(f"Loaded {len(food)} rows from Food Delivery")
        dfs.append(food)
        
    # Mini E-Commerce excluded due to incompatible target scales (days vs minutes)
        
    nyc = process_nyc_taxi()
    if not nyc.empty:
        print(f"Loaded {len(nyc)} rows from NYC Taxi")
        dfs.append(nyc)
        
    amzn = process_amazon_last_mile()
    if not amzn.empty:
        print(f"Loaded {len(amzn)} rows from Amazon Last Mile")
        dfs.append(amzn)
        
    if not dfs:
        print("No Track A datasets found.")
        return
        
    final_cols = [
        'order_id', 'created_at', 'pickup_lat', 'pickup_lng', 'delivery_lat', 'delivery_lng',
        'vehicle_type', 'priority', 'status', 'weather_severity', 'traffic_score', 'actual_delivery_time_minutes',
        'source_dataset'
    ]
    
    # Cast order_id to string to avoid schema conflicts
    for df in dfs:
        df['order_id'] = df['order_id'].astype(str)
        
    combined = pd.concat(dfs, ignore_index=True)
    # Ensure all columns exist
    for col in final_cols:
        if col not in combined.columns:
            combined[col] = None
            
    df_out = combined[final_cols]
    
    out_path = "transit/data/processed/track_a_combined.parquet"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df_out.to_parquet(out_path, index=False)
    print(f"Saved {len(df_out)} combined rows to {out_path}")

if __name__ == "__main__":
    combine_track_a()
