import numpy as np
from src.models.evaluate import evaluate_model, pinball_loss

def test_evaluate_metrics_numerical_correctness():
    """
    Asserts MAE/RMSE/R2 and pinball loss produce numerically correct values
    against a hand-computed known-answer example.
    """
    y_true = np.array([10, 20, 30])
    y_pred_p50 = np.array([12, 18, 30])
    
    # Errors: +2, -2, 0. 
    # MAE = (2 + 2 + 0) / 3 = 1.333...
    # MSE = (4 + 4 + 0) / 3 = 2.666...
    # RMSE = sqrt(2.666) = 1.63299
    # R2 = 1 - (8 / sum((y - 20)^2)) = 1 - (8 / (100 + 0 + 100)) = 1 - (8/200) = 0.96
    
    metrics = evaluate_model(y_true, y_pred_p50)
    
    assert np.isclose(metrics['MAE'], 4/3)
    assert np.isclose(metrics['RMSE'], np.sqrt(8/3))
    assert np.isclose(metrics['R2'], 0.96)
    
    # Test Pinball Loss
    # For alpha = 0.5:
    # diff = y_true - y_pred_p50 = [-2, 2, 0]
    # max(0.5 * -2, -0.5 * -2) = max(-1, 1) = 1
    # max(0.5 * 2, -0.5 * 2) = max(1, -1) = 1
    # max(0, 0) = 0
    # Mean pinball loss = 2/3
    loss_p50 = pinball_loss(y_true, y_pred_p50, alpha=0.5)
    assert np.isclose(loss_p50, 2/3)
