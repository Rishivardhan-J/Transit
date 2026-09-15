import pandas as pd
import numpy as np
import pickle
import os
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

class SpatialDistanceTransformer(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        self.is_fitted_ = True
        return self
        
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X_out = X.copy()
        if 'pickup_lat' in X_out.columns and 'delivery_lat' in X_out.columns:
            dx = X_out['pickup_lat'] - X_out['delivery_lat']
            dy = X_out['pickup_lng'] - X_out['delivery_lng']
            X_out['euclidean_distance'] = np.sqrt(dx**2 + dy**2)
        return X_out

class CategoricalEncoder(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.encoder = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
        self.cat_cols = []
        
    def fit(self, X: pd.DataFrame, y=None):
        X_out = X.copy()
        cols_to_drop = ['order_id', 'created_at', 'source_dataset']
        if 'actual_delivery_time_minutes' in X_out.columns:
            cols_to_drop.append('actual_delivery_time_minutes')
            
        X_out = X_out.drop(columns=[c for c in cols_to_drop if c in X_out.columns], errors='ignore')
        
        self.cat_cols = X_out.select_dtypes(include=['object', 'category']).columns.tolist()
        if self.cat_cols:
            self.encoder.fit(X_out[self.cat_cols])
            
        self.is_fitted_ = True
        return self
        
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X_out = X.copy()
        cols_to_drop = ['order_id', 'created_at', 'source_dataset']
        if 'actual_delivery_time_minutes' in X_out.columns:
            cols_to_drop.append('actual_delivery_time_minutes')
            
        X_out = X_out.drop(columns=[c for c in cols_to_drop if c in X_out.columns], errors='ignore')
        
        if self.cat_cols:
            cols_to_encode = [c for c in self.cat_cols if c in X_out.columns]
            if cols_to_encode:
                X_out[cols_to_encode] = self.encoder.transform(X_out[cols_to_encode])
        return X_out

def build_feature_pipeline() -> Pipeline:
    return Pipeline([
        ('spatial', SpatialDistanceTransformer()),
        ('encoder', CategoricalEncoder())
    ])

def save_pipeline(pipeline: Pipeline, output_dir: str = "transit/results/models") -> str:
    import datetime
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%M%d_%H%M%S")
    filepath = os.path.join(output_dir, f"feature_pipeline_{timestamp}_unset.pkl")
    with open(filepath, 'wb') as f:
        pickle.dump(pipeline, f)
    return filepath

def load_pipeline(filepath: str) -> Pipeline:
    with open(filepath, 'rb') as f:
        return pickle.load(f)
