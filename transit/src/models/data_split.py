import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

# EXPLICIT PROHIBITION: Random k-fold CV or train_test_split(shuffle=True) is strictly prohibited 
# on this data to avoid temporal leakage. Always use time-based splitting based on `created_at`.

def chronological_split(df: pd.DataFrame, time_col: str = 'created_at', 
                        train_ratio: float = 0.70, val_ratio: float = 0.15):
    """
    Splits the dataframe into chronological train, validation, and test sets.
    """
    if time_col not in df.columns:
        raise ValueError(f"Time column {time_col} not found in dataframe.")
    
    # Ensure dataframe is sorted by time
    df_sorted = df.sort_values(by=time_col).reset_index(drop=True)
    
    n = len(df_sorted)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)
    
    train_df = df_sorted.iloc[:train_end].copy()
    val_df = df_sorted.iloc[train_end:val_end].copy()
    test_df = df_sorted.iloc[val_end:].copy()
    
    return train_df, val_df, test_df

def get_time_series_cv(n_splits: int = 5):
    """
    Returns a TimeSeriesSplit object for cross-validation during hyperparameter search.
    """
    return TimeSeriesSplit(n_splits=n_splits)
