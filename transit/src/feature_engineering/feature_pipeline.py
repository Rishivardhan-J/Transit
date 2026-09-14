import pandas as pd
import numpy as np
import pickle
import os
from datetime import datetime
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from src.feature_engineering.features import compute_distance_features, compute_time_features


class DistanceFeatureTransformer(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        self.is_fitted_ = True
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X_out = X.copy()
        return compute_distance_features(X_out)


class TimeFeatureTransformer(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        self.is_fitted_ = True
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X_out = X.copy()
        if 'time_window_start' in X_out.columns and 'time_window_end' in X_out.columns:
            # Ensure datetime type
            X_out['time_window_start'] = pd.to_datetime(X_out['time_window_start'])
            X_out['time_window_end'] = pd.to_datetime(X_out['time_window_end'])
            return compute_time_features(X_out)
        return X_out


class PassThroughTransformer(BaseEstimator, TransformerMixin):
    """Simple transformer to ensure dataframe structure is maintained if needed."""
    def fit(self, X, y=None):
        self.is_fitted_ = True
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return X.copy()


def build_feature_pipeline() -> Pipeline:
    """
    Builds the definitive sklearn Pipeline for all feature transformations.
    This is the single source of truth for features.
    """
    pipeline = Pipeline(steps=[
        ('distance_features', DistanceFeatureTransformer()),
        ('time_features', TimeFeatureTransformer())
        # We can add a ColumnTransformer here later if we want to isolate features
        # e.g., categorical encoding for specific models, but tree models often 
        # take native categoricals.
    ])
    return pipeline


def save_pipeline(pipeline: Pipeline, output_dir: str = "transit/results/models") -> str:
    """
    Saves the fitted pipeline with versioning metadata (timestamp + git_hash).
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    git_hash = "unset"  # Placeholder for Phase 1
    
    filename = f"feature_pipeline_{timestamp}_{git_hash}.pkl"
    filepath = os.path.join(output_dir, filename)
    
    metadata = {
        'timestamp': timestamp,
        'git_hash': git_hash,
        'pipeline': pipeline
    }
    
    with open(filepath, 'wb') as f:
        pickle.dump(metadata, f)
        
    return filepath


def load_pipeline(filepath: str) -> Pipeline:
    """
    Loads a saved feature pipeline.
    """
    with open(filepath, 'rb') as f:
        metadata = pickle.load(f)
    return metadata['pipeline']
