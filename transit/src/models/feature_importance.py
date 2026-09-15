import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.inspection import permutation_importance
import os

def compute_and_plot_importance(model, X_val, y_val, feature_names, 
                                output_path="transit/results/figures/feature_importance_comparison.png"):
    """
    Computes both impurity-based (if available) and permutation-based feature importance.
    Plots them side-by-side for cross-checking.
    """
    # 1. Impurity importance (Tree models)
    impurity_importances = None
    if hasattr(model, 'feature_importances_'):
        impurity_importances = model.feature_importances_
    
    # 2. Permutation importance
    result = permutation_importance(model, X_val, y_val, n_repeats=5, random_state=42, n_jobs=-1)
    permutation_importances = result.importances_mean
    
    # Normalize for easier comparison (relative importance)
    if impurity_importances is not None:
        impurity_importances = impurity_importances / np.max(impurity_importances)
    permutation_importances = permutation_importances / np.max(permutation_importances)
    
    # Prepare dataframe
    data = {'Permutation': permutation_importances}
    if impurity_importances is not None:
        data['Impurity'] = impurity_importances
        
    df_imp = pd.DataFrame(data, index=feature_names)
    
    # Sort by Permutation importance for readability
    df_imp = df_imp.sort_values(by='Permutation', ascending=True)
    
    # Plot side-by-side
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    df_imp.plot(kind='barh', ax=ax, color=['lightcoral', 'skyblue'] if impurity_importances is not None else ['lightcoral'])
    ax.set_title('Feature Importance: Permutation vs Impurity')
    ax.set_xlabel('Normalized Importance')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    
    return df_imp
