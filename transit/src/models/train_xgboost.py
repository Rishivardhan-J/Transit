import os
import argparse
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import RandomizedSearchCV
import mlflow
import mlflow.xgboost

from src.models.config import RANDOM_SEED
from src.models.data_split import chronological_split, get_time_series_cv
from src.models.evaluate import evaluate_model
from src.models.model_registry import save_model
from src.feature_engineering.feature_pipeline import load_pipeline

def train_xgb(data_path: str, pipeline_path: str, dataset_name: str):
    """
    Trains XGBoost models for p10, p50, p90 quantiles.
    Logs to MLflow.
    """
    # Setup MLflow
    mlflow_uri = "file:" + os.path.abspath("transit/results/mlruns")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment(f"Transit_Phase2_{dataset_name}")
    
    print(f"Loading data from {data_path}...")
    df = pd.read_parquet(data_path)
    pipeline = load_pipeline(pipeline_path)
    
    train_df, val_df, test_df = chronological_split(df, time_col='created_at')
    
    X_train_raw = train_df.drop(columns=['actual_delivery_time_minutes', 'created_at'])
    y_train = train_df['actual_delivery_time_minutes'].values
    
    X_test_raw = test_df.drop(columns=['actual_delivery_time_minutes', 'created_at'])
    y_test = test_df['actual_delivery_time_minutes'].values
    
    print("Transforming features...")
    X_train = pipeline.transform(X_train_raw)
    X_test = pipeline.transform(X_test_raw)
    
    with mlflow.start_run(run_name="XGBoost_Quantiles"):
        mlflow.log_param("model_type", "xgboost")
        mlflow.log_param("dataset", dataset_name)
        mlflow.log_param("random_seed", RANDOM_SEED)
        
        pipeline_version = os.path.basename(pipeline_path).replace('feature_pipeline_', '').replace('.pkl', '')
        mlflow.log_param("pipeline_version", pipeline_version)
        
        print("Tuning hyperparameters on p50...")
        base_model = xgb.XGBRegressor(
            objective='reg:quantileerror',
            quantile_alpha=0.5,
            random_state=RANDOM_SEED,
            n_jobs=-1
        )
        
        param_dist = {
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.05, 0.1],
            'n_estimators': [100, 200, 500],
            'subsample': [0.8, 1.0]
        }
        
        tscv = get_time_series_cv(n_splits=3)
        random_search = RandomizedSearchCV(
            estimator=base_model,
            param_distributions=param_dist,
            n_iter=5,
            cv=tscv,
            scoring='neg_mean_absolute_error',
            random_state=RANDOM_SEED,
            n_jobs=-1
        )
        
        random_search.fit(X_train, y_train)
        best_params = random_search.best_params_
        mlflow.log_params(best_params)
        print(f"Best params: {best_params}")
        
        models = {}
        predictions = {}
        
        for alpha in [0.1, 0.5, 0.9]:
            print(f"Training XGBoost alpha={alpha}...")
            model = xgb.XGBRegressor(
                objective='reg:quantileerror',
                quantile_alpha=alpha,
                random_state=RANDOM_SEED,
                n_jobs=-1,
                **best_params
            )
            model.fit(X_train, y_train)
            models[f'p{int(alpha*100)}'] = model
            predictions[f'p{int(alpha*100)}'] = model.predict(X_test)
            
        metrics = evaluate_model(
            y_test, 
            predictions['p50'], 
            predictions['p10'], 
            predictions['p90']
        )
        mlflow.log_metrics(metrics)
        print(f"Test Metrics: {metrics}")
        
        for name, model in models.items():
            metadata = {
                'alpha': float(name.replace('p', ''))/100,
                'pipeline_version': pipeline_version,
                'model_type': 'xgboost',
                'best_params': best_params
            }
            model_dir = save_model(model, f"xgboost_{name}", metadata)
            
            mlflow.xgboost.log_model(model, f"model_{name}")
            print(f"Saved {name} to {model_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="Path to processed parquet data")
    parser.add_argument("--pipeline", type=str, required=True, help="Path to fitted feature_pipeline pkl")
    parser.add_argument("--name", type=str, default="track_a", help="Dataset name for logging")
    args = parser.parse_args()
    
    train_xgb(args.data, args.pipeline, args.name)
