import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import os

def pinball_loss(y_true, y_pred, alpha):
    """Computes the pinball loss (quantile loss) for a given quantile alpha."""
    diff = y_true - y_pred
    return np.mean(np.maximum(alpha * diff, (alpha - 1) * diff))

def empirical_coverage(y_true, y_pred_lower, y_pred_upper):
    """Computes the fraction of true values that fall within the prediction interval."""
    coverage = np.mean((y_true >= y_pred_lower) & (y_true <= y_pred_upper))
    return coverage

def evaluate_model(y_true, y_pred_p50, y_pred_p10=None, y_pred_p90=None):
    """
    Computes standard and quantile metrics.
    """
    metrics = {
        'MAE': mean_absolute_error(y_true, y_pred_p50),
        'RMSE': np.sqrt(mean_squared_error(y_true, y_pred_p50)),
        'R2': r2_score(y_true, y_pred_p50)
    }
    
    if y_pred_p10 is not None and y_pred_p90 is not None:
        metrics['Pinball_Loss_p10'] = pinball_loss(y_true, y_pred_p10, 0.1)
        metrics['Pinball_Loss_p50'] = pinball_loss(y_true, y_pred_p50, 0.5)
        metrics['Pinball_Loss_p90'] = pinball_loss(y_true, y_pred_p90, 0.9)
        metrics['Coverage_80'] = empirical_coverage(y_true, y_pred_p10, y_pred_p90)
        
    return metrics

def plot_model_comparison(metrics_dict, output_path="transit/results/figures/model_comparison.png"):
    """
    Plots a comparison of standard metrics (MAE, RMSE, R2) across models.
    metrics_dict format: {'ModelName': {'MAE': 10, 'RMSE': 12, 'R2': 0.8}, ...}
    """
    df = pd.DataFrame(metrics_dict).T
    if df.empty:
        return
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path.replace(".png", ".csv"))
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # MAE
    df['MAE'].plot(kind='bar', ax=axes[0], color='skyblue')
    axes[0].set_title('MAE (Lower is Better)')
    axes[0].set_ylabel('Minutes')
    
    # RMSE
    df['RMSE'].plot(kind='bar', ax=axes[1], color='lightcoral')
    axes[1].set_title('RMSE (Lower is Better)')
    axes[1].set_ylabel('Minutes')
    
    # R2
    df['R2'].plot(kind='bar', ax=axes[2], color='lightgreen')
    axes[2].set_title('R² Score (Higher is Better)')
    axes[2].set_ylim(0, 1.0)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
