import shap
import pandas as pd
import matplotlib.pyplot as plt
import os

class ExplainerWrapper:
    def __init__(self, model):
        # TreeExplainer is fast and exact for tree-based models (LGBM, RF, XGB)
        self.explainer = shap.TreeExplainer(model)
        
    def explain_prediction(self, features_df: pd.DataFrame, top_k: int = 5) -> list:
        """
        Explains a single prediction (or small batch).
        Returns a list of dictionaries formatted for the Prediction schema:
        [{"feature": "traffic_score", "value": 0.82, "impact_minutes": 4.3}, ...]
        """
        shap_values = self.explainer.shap_values(features_df)
        
        # shap_values could be a list (multi-class) or an array
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
            
        results = []
        for i in range(len(features_df)):
            row_shap = shap_values[i]
            row_features = features_df.iloc[i]
            
            # Sort by absolute SHAP value (impact magnitude)
            sorted_indices = sorted(range(len(row_shap)), key=lambda k: abs(row_shap[k]), reverse=True)
            
            top_features = []
            for idx in sorted_indices[:top_k]:
                feature_name = features_df.columns[idx]
                feature_val = row_features.iloc[idx]
                impact = float(row_shap[idx])
                
                top_features.append({
                    "feature": feature_name,
                    "value": float(feature_val) if isinstance(feature_val, (int, float)) else str(feature_val),
                    "impact_minutes": round(impact, 2)
                })
                
            results.append(top_features)
            
        # If single row passed, return single list
        if len(results) == 1:
            return results[0]
        return results

def plot_global_shap_summary(model, X_val, output_path="transit/results/figures/shap_summary.png"):
    """
    Produces a global SHAP summary plot (beeswarm).
    """
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_val)
    
    if isinstance(shap_values, list):
        shap_values = shap_values[0]
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_val, show=False)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
