import os
import argparse
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import mlflow
import mlflow.sklearn

from src.models.config import RANDOM_SEED
from src.models.data_split import chronological_split
from src.models.evaluate import evaluate_model
from src.models.model_registry import save_model
from src.feature_engineering.feature_pipeline import load_pipeline

def train_rf(data_path: str, pipeline_path: str, dataset_name: str):
    """
    Trains a Random Forest baseline for p50 (point estimate).
    Logs to MLflow.
    """
    # Setup MLflow
    mlflow_uri = "file:" + os.path.abspath("transit/results/mlruns")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment(f"Transit_Phase2_{dataset_name}")
    
    print(f"Loading data from {data_path}...")
    df = pd.read_parquet(data_path)
    pipeline = load_pipeline(pipeline_path)
    
    # 1. Split Data (Chronological)
    train_df, val_df, test_df = chronological_split(df, time_col='created_at')
    
    X_train_raw = train_df.drop(columns=['actual_delivery_time_minutes', 'created_at'])
    y_train = train_df['actual_delivery_time_minutes'].values
    
    X_test_raw = test_df.drop(columns=['actual_delivery_time_minutes', 'created_at'])
    y_test = test_df['actual_delivery_time_minutes'].values
    
    # 2. Transform Features
    print("Transforming features...")
    # The pipeline's CategoricalEncoderTransformer now returns ordinal integers
    # which Random Forest will treat as numerical. It's a standard baseline approach.
    X_train = pipeline.transform(X_train_raw)
    X_test = pipeline.transform(X_test_raw)
    
    with mlflow.start_run(run_name="RandomForest_Baseline"):
        mlflow.log_param("model_type", "random_forest")
        mlflow.log_param("dataset", dataset_name)
        mlflow.log_param("random_seed", RANDOM_SEED)
        
        pipeline_version = os.path.basename(pipeline_path).replace('feature_pipeline_', '').replace('.pkl', '')
        mlflow.log_param("pipeline_version", pipeline_version)
        
        # 3. Train Model
        print("Training Random Forest...")
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=10,
            random_state=RANDOM_SEED,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        
        # 4. Evaluate
        y_pred = model.predict(X_test)
        metrics = evaluate_model(y_test, y_pred)
        mlflow.log_metrics(metrics)
        print(f"Test Metrics: {metrics}")
        
        # 5. Save Model
        metadata = {
            'pipeline_version': pipeline_version,
            'model_type': 'random_forest'
        }
        model_dir = save_model(model, "random_forest_p50", metadata)
        
        mlflow.sklearn.log_model(model, "model_p50")
        print(f"Saved to {model_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="Path to processed parquet data")
    parser.add_argument("--pipeline", type=str, required=True, help="Path to fitted feature_pipeline pkl")
    parser.add_argument("--name", type=str, default="track_a", help="Dataset name for logging")
    args = parser.parse_args()
    
    train_rf(args.data, args.pipeline, args.name)
