import pandas as pd
from typing import Dict, Any

from src.data_processing.schemas import Order, Vehicle, Prediction
from src.feature_engineering.feature_pipeline import load_pipeline
from src.models.model_registry import load_model
from src.models.explainability import ExplainerWrapper

import logging

logger = logging.getLogger(__name__)

# Global cache to prevent reloading models/pipelines for every request
_pipeline_cache = None
_models_cache = {}
_explainer_cache = None
_model_version_str = "lightgbm_latest"

def init_models(pipeline_path: str = None, model_versions: Dict[str, str] = None):
    """
    Initializes and caches the models, pipeline, and SHAP explainer.
    If model_versions is None, loads 'latest'.
    """
    global _pipeline_cache, _models_cache, _explainer_cache, _model_version_str
    
    if pipeline_path is None:
        # Default fallback - this assumes the latest pipeline is used in production.
        # In a real system, you'd specify exactly which pipeline.
        raise ValueError("Must provide pipeline_path to prevent train/serve skew.")
        
    _pipeline_cache = load_pipeline(pipeline_path)
    
    if model_versions is None:
        model_versions = {'p10': 'latest', 'p50': 'latest', 'p90': 'latest'}
        
    for q in ['p10', 'p50', 'p90']:
        model, meta = load_model(f"lightgbm_{q}", version=model_versions[q])
        _models_cache[q] = model
        if q == 'p50':
            pipe_ver = meta.get('pipeline_version', 'latest') if isinstance(meta, dict) else 'latest'
            _model_version_str = f"lightgbm_{pipe_ver}"
            logger.info(f"Loaded ML model lightgbm_p50 from {pipeline_path} (model_version: {_model_version_str})")
            print(f"Loaded ML model lightgbm_p50 from {pipeline_path} (model_version: {_model_version_str})", flush=True)
        
    _explainer_cache = ExplainerWrapper(_models_cache['p50'])

def predict_delivery_time(order: Order, vehicle: Vehicle, as_of_timestamp: str, pipeline_path: str) -> Prediction:
    """
    Inference entrypoint.
    Returns a fully populated Prediction object including uncertainty bounds and SHAP explanations.
    """
    if _pipeline_cache is None or not _models_cache:
        init_models(pipeline_path)
        
    # Construct raw DataFrame from schemas
    row = {
        **order.model_dump(),
        **vehicle.model_dump(),
        'as_of_timestamp': as_of_timestamp
    }
    # Flatten nested dictionaries if necessary, but Phase 1 schemas are flat
    raw_df = pd.DataFrame([row])
    
    # Add external factors missing from Order/Vehicle schemas that the model expects
    if 'weather_severity' not in raw_df.columns:
        raw_df['weather_severity'] = 'clear'
    if 'traffic_score' not in raw_df.columns:
        raw_df['traffic_score'] = 1.0
    
    # 1. Feature Engineering
    features_df = _pipeline_cache.transform(raw_df)
    
    # Need to drop any target or leakage columns if they accidentally leaked in, though schemas shouldn't have them
    cols_to_drop = ['actual_delivery_time_minutes', 'created_at', 'as_of_timestamp']
    features_df = features_df.drop(columns=[c for c in cols_to_drop if c in features_df.columns])
    
    # Filter only the columns the model expects (avoid dtype errors on metadata)
    expected_cols = _models_cache['p50'].feature_name_
    features_df = features_df[[c for c in expected_cols if c in features_df.columns]]
    
    # 2. Predict Quantiles
    p10_pred = _models_cache['p10'].predict(features_df)[0]
    p50_pred = _models_cache['p50'].predict(features_df)[0]
    p90_pred = _models_cache['p90'].predict(features_df)[0]
    
    # Monotonic sorting to ensure p10 <= p50 <= p90 and ge 0.0
    p10_val, p50_val, p90_val = sorted([max(0.0, float(p10_pred)), max(0.0, float(p50_pred)), max(0.0, float(p90_pred))])
    
    # 3. Explainability
    shap_explanation = _explainer_cache.explain_prediction(features_df, top_k=5)
    
    # 4. Construct Output Schema
    return Prediction(
        order_id=order.order_id,
        predicted_time_p10=p10_val,
        predicted_time_p50=p50_val,
        predicted_time_p90=p90_val,
        model_version=_model_version_str,
        shap_top_features=shap_explanation
    )
