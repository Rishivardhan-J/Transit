import os
import argparse
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import RandomizedSearchCV
import mlflow
import mlflow.lightgbm

from src.models.config import RANDOM_SEED
from src.models.data_split import chronological_split, get_time_series_cv
from src.models.evaluate import evaluate_model, pinball_loss
from src.models.model_registry import save_model
from src.feature_engineering.feature_pipeline import load_pipeline

def train_lgbm(data_path: str, pipeline_path: str, dataset_name: str):
    """
    Trains LightGBM models for p10, p50, p90 quantiles.
    Logs to MLflow.
    """
    # Setup MLflow
    mlflow.set_tracking_uri("sqlite:///mlruns.db")
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
    X_train = pipeline.transform(X_train_raw)
    X_test = pipeline.transform(X_test_raw)
    
    # Identify categorical columns (OrdinalEncoder converts to numeric, but we tell LGBM they are categorical)
    cat_cols = [c for c in X_train.columns if c in pipeline.named_steps['categorical_encoder'].cat_cols]
    
    with mlflow.start_run(run_name="LightGBM_Quantiles"):
        mlflow.log_param("model_type", "lightgbm")
        mlflow.log_param("dataset", dataset_name)
        mlflow.log_param("random_seed", RANDOM_SEED)
        
        # Log Pipeline Version from metadata filename
        pipeline_version = os.path.basename(pipeline_path).replace('feature_pipeline_', '').replace('.pkl', '')
        mlflow.log_param("pipeline_version", pipeline_version)
        
        # 3. Hyperparameter Tuning (on p50 only to save time)
        print("Tuning hyperparameters on p50...")
        base_model = lgb.LGBMRegressor(
            objective='quantile', 
            alpha=0.5, 
            random_state=RANDOM_SEED, 
            n_jobs=-1,
            verbosity=-1
        )
        
        param_dist = {
            'num_leaves': [31, 63, 127],
            'max_depth': [-1, 7, 10],
            'learning_rate': [0.01, 0.05, 0.1],
            'n_estimators': [100, 200, 500],
            'min_child_samples': [10, 20, 50]
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
        
        # Convert categoricals to 'category' dtype for LGBM or just pass categorical_feature in fit
        # LGBM sklearn API uses categorical_feature in fit()
        random_search.fit(
            X_train, y_train, 
            categorical_feature=cat_cols
        )
        
        best_params = random_search.best_params_
        mlflow.log_params(best_params)
        print(f"Best params: {best_params}")
        
        # 4. Train Final Quantile Models
        models = {}
        predictions = {}
        
        for alpha in [0.1, 0.5, 0.9]:
            print(f"Training LightGBM alpha={alpha}...")
            model = lgb.LGBMRegressor(
                objective='quantile', 
                alpha=alpha, 
                random_state=RANDOM_SEED, 
                n_jobs=-1,
                verbosity=-1,
                **best_params
            )
            model.fit(
                X_train, y_train,
                categorical_feature=cat_cols
            )
            models[f'p{int(alpha*100)}'] = model
            predictions[f'p{int(alpha*100)}'] = model.predict(X_test)
            
        # 5. Evaluate
        metrics = evaluate_model(
            y_test, 
            predictions['p50'], 
            predictions['p10'], 
            predictions['p90']
        )
        mlflow.log_metrics(metrics)
        print(f"Test Metrics: {metrics}")
        
        # 6. Save Models
        for name, model in models.items():
            metadata = {
                'alpha': float(name.replace('p', ''))/100,
                'pipeline_version': pipeline_version,
                'model_type': 'lightgbm',
                'best_params': best_params
            }
            model_dir = save_model(model, f"lightgbm_{name}", metadata)
            
            # Log as MLflow artifact
            mlflow.lightgbm.log_model(model, f"model_{name}")
            print(f"Saved {name} to {model_dir}")
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="Path to processed parquet data")
    parser.add_argument("--pipeline", type=str, required=True, help="Path to fitted feature_pipeline pkl")
    parser.add_argument("--name", type=str, default="track_a", help="Dataset name for logging")
    args = parser.parse_args()
    
    train_lgbm(args.data, args.pipeline, args.name)
