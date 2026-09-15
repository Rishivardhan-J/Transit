import pandas as pd
import pytest
from src.models.data_split import chronological_split

def test_chronological_ordering():
    """
    Asserts that every timestamp in the train set is strictly earlier than 
    every timestamp in the validation set, and every validation timestamp 
    is strictly earlier than every test timestamp.
    """
    # Create synthetic dataset with out-of-order dates
    dates = pd.date_range(start="2024-01-01", periods=100, freq='D')
    df = pd.DataFrame({'created_at': dates, 'val': range(100)})
    
    # Shuffle the dataframe to ensure split logic sorts it correctly
    df_shuffled = df.sample(frac=1.0, random_state=42)
    
    train_df, val_df, test_df = chronological_split(df_shuffled, time_col='created_at', train_ratio=0.7, val_ratio=0.15)
    
    assert len(train_df) == 70
    assert len(val_df) == 15
    assert len(test_df) == 15
    
    max_train_date = train_df['created_at'].max()
    min_val_date = val_df['created_at'].min()
    max_val_date = val_df['created_at'].max()
    min_test_date = test_df['created_at'].min()
    
    assert max_train_date < min_val_date, "Leakage: Train date overlaps with Validation"
    assert max_val_date < min_test_date, "Leakage: Validation date overlaps with Test"
    
    # Also verify data wasn't randomly sampled (time should be monotonic within splits)
    assert train_df['created_at'].is_monotonic_increasing
    assert val_df['created_at'].is_monotonic_increasing
    assert test_df['created_at'].is_monotonic_increasing
