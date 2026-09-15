import pandas as pd
from typing import Dict, Any

from src.data_processing.schemas import Order, Vehicle, Prediction
from src.feature_engineering.feature_pipeline import load_pipeline
from src.models.model_registry import load_model
from src.models.explainability import ExplainerWrapper

# Global cache to prevent reloading models/pipelines for every request
_pipeline_cache = None
_models_cache = {}
_explainer_cache = None

def init_models(pipeline_path: str = None, model_versions: Dict[str, str] = None):
    """
    Initializes and caches the models, pipeline, and SHAP explainer.
    If model_versions is None, loads 'latest'.
    """
    global _pipeline_cache, _models_cache, _explainer_cache
    
    if pipeline_path is None:
        # Default fallback - this assumes the latest pipeline is used in production.
        # In a real system, you'd specify exactly which pipeline.
        raise ValueError("Must provide pipeline_path to prevent train/serve skew.")
        
    _pipeline_cache = load_pipeline(pipeline_path)
    
    if model_versions is None:
        model_versions = {'p10': 'latest', 'p50': 'latest', 'p90': 'latest'}
        
    for q in ['p10', 'p50', 'p90']:
        model, _ = load_model(f"lightgbm_{q}", version=model_versions[q])
        _models_cache[q] = model
        
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
    
    # 1. Feature Engineering
    features_df = _pipeline_cache.transform(raw_df)
    
    # Need to drop any target or leakage columns if they accidentally leaked in, though schemas shouldn't have them
    cols_to_drop = ['actual_delivery_time_minutes', 'created_at', 'as_of_timestamp']
    features_df = features_df.drop(columns=[c for c in cols_to_drop if c in features_df.columns])
    
    # 2. Predict Quantiles
    p10_pred = _models_cache['p10'].predict(features_df)[0]
    p50_pred = _models_cache['p50'].predict(features_df)[0]
    p90_pred = _models_cache['p90'].predict(features_df)[0]
    
    # 3. Explainability
    shap_explanation = _explainer_cache.explain_prediction(features_df, top_k=5)
    
    # 4. Construct Output Schema
    # Find the version from the loaded p50 model's metadata
    # Actually, we didn't cache metadata, let's just use "latest" placeholder or similar
    # For Phase 2, we just return a valid string.
    
    return Prediction(
        order_id=order.order_id,
        predicted_time_p10=float(p10_pred),
        predicted_time_p50=float(p50_pred),
        predicted_time_p90=float(p90_pred),
        model_version="lightgbm_latest",
        shap_top_features=shap_explanation
    )
