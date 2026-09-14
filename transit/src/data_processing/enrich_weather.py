import pandas as pd
from datetime import datetime
from meteostat import Point, hourly
import logging

logger = logging.getLogger(__name__)

def enrich_weather(df: pd.DataFrame, date_col: str = 'time_window_start', lat_col: str = 'pickup_lat', lng_col: str = 'pickup_lng') -> pd.DataFrame:
    """
    Enriches the dataset with historical weather data using the Meteostat library.
    It fetches data for the date of the order at the pickup location.
    """
    df_enriched = df.copy()
    
    if df_enriched.empty:
        return df_enriched

    # Ensure datetime
    df_enriched[date_col] = pd.to_datetime(df_enriched[date_col])
    
    weather_data_list = []
    
    # In a production scenario, we'd batch this by geographic region to avoid 
    # hitting the API per-row. For Phase 1, we approximate by finding a central 
    # point per date, or doing it per unique location.
    # Here, we group by date and rough location (rounded lat/lng) to minimize calls.
    
    df_enriched['date_only'] = df_enriched[date_col].dt.date
    df_enriched['round_lat'] = df_enriched[lat_col].round(1)
    df_enriched['round_lng'] = df_enriched[lng_col].round(1)
    
    groups = df_enriched.groupby(['date_only', 'round_lat', 'round_lng'])
    
    for (d, lat, lng), group in groups:
        try:
            start = datetime(d.year, d.month, d.day)
            end = datetime(d.year, d.month, d.day, 23, 59, 59)
            
            location = Point(lat, lng)
            data = hourly(location, start, end)
            data = data.fetch()
            
            if not data.empty:
                # Average weather for the day in that region
                mean_temp = data['temp'].mean()
                mean_precip = data['prcp'].mean()
                mean_wind = data['wspd'].mean()
            else:
                mean_temp = None
                mean_precip = None
                mean_wind = None
                
            for idx in group.index:
                weather_data_list.append({
                    'index': idx,
                    'temp_c': mean_temp,
                    'precip_mm': mean_precip,
                    'wind_kmh': mean_wind
                })
        except Exception as e:
            logger.warning(f"Failed to fetch weather for {d} at {lat},{lng}: {e}")
            for idx in group.index:
                weather_data_list.append({
                    'index': idx,
                    'temp_c': None,
                    'precip_mm': None,
                    'wind_kmh': None
                })
                
    weather_df = pd.DataFrame(weather_data_list).set_index('index')
    
    # Join back
    df_enriched = df_enriched.join(weather_df)
    
    # Compute weather severity (simple heuristic)
    # E.g. high precip or high wind increases severity
    df_enriched['weather_severity'] = 1.0 # Base severity
    if 'precip_mm' in df_enriched.columns:
        df_enriched.loc[df_enriched['precip_mm'] > 5.0, 'weather_severity'] += 0.5
    if 'wind_kmh' in df_enriched.columns:
        df_enriched.loc[df_enriched['wind_kmh'] > 30.0, 'weather_severity'] += 0.5
        
    # Cleanup temps
    df_enriched.drop(columns=['date_only', 'round_lat', 'round_lng'], inplace=True)
        
    return df_enriched
