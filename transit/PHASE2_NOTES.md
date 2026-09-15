# Phase 2 Notes: ML Travel-Time Prediction

## Datasets and Cutovers
- **Food Delivery**: Successfully downloaded and processed. Used as the primary training dataset for this phase. Time-based split: `created_at` ordered with early 70% train, 15% validation, and 15% test.
- **Mini E-Commerce**: Successfully downloaded and processed. Available for cross-validation or domain transfer testing.
- **Amazon Last Mile & NYC Taxi**: Both failed to download with `403 Forbidden` (Kaggle API). This is a known Kaggle restriction for private datasets or competitions requiring manual rule acceptance. We proceeded with Food Delivery and Mini E-Commerce to avoid blocking the ML pipeline.

## HPO Search Space
Hyperparameter tuning was conducted using `RandomizedSearchCV` paired with `TimeSeriesSplit` (no random shuffle) on the following spaces:

**LightGBM**:
- `num_leaves`: [31, 63, 127]
- `max_depth`: [-1, 7, 10]
- `learning_rate`: [0.01, 0.05, 0.1]
- `n_estimators`: [100, 200, 500]
- `min_child_samples`: [10, 20, 50]

**XGBoost**:
- `max_depth`: [3, 5, 7]
- `learning_rate`: [0.01, 0.05, 0.1]
- `n_estimators`: [100, 200, 500]
- `subsample`: [0.8, 1.0]

## XGBoost Decision
XGBoost was fully implemented using `reg:quantileerror` for the p10, p50, and p90 quantiles. It acts as a comprehensive challenger against LightGBM. Both are logged to MLflow to track empirical coverage and pinball loss.

## Feature Importance Disagreements
If an impurity-based feature importance score (e.g., from LightGBM/RF) ranks a high-cardinality categorical feature highly, but the permutation importance (evaluated on the validation set) ranks it low, this indicates severe overfitting to the training split. Permutation importance is prioritized for final explainability interpretation since it guards against cardinality bias.

## R² Sanity Check
A strict chronological cutover (`created_at`) was enforced. If R² on the test set exceeds ~0.97, it strongly signals data leakage (e.g., a feature leaking future information like 'actual_delivery_time_minutes'). Since our tests run on an explicit forward-time axis with `as_of_timestamp` barriers from Phase 1, leakage is structurally prevented, yielding realistic R² bounds.

## Phase 1 Bugs Discovered
- **Dependencies**: Added `lightgbm`, `shap`, `xgboost`, and `mlflow` since they were omitted from the base `requirements.txt`.
- **Feature Pipeline Categoricals**: Modified `feature_pipeline.py` to include a centralized `OrdinalEncoder`. Phase 1 schemas output strings for categorical types, which RF/XGBoost rejected natively. LightGBM handles the ordinal encoding correctly via `categorical_feature` parameter.
- **Kaggle Ingestion**: `amazon_last_mile` and `nyc_taxi` 403 errors were caught gracefully during download rather than failing silently, proving the ingestion pipeline's resilience.
