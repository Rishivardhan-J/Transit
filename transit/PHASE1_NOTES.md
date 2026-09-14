# Phase 1 Notes

Documenting reasonable decisions and judgments made during Phase 1.

## Data Processing
- **Missing Value Imputation**: Defaulted to median for numerical and 'unknown' for categorical. Configurable via a dictionary per-field in the `DataProcessor`.
- **Validation**: Enforced via Pydantic models. We collect all errors per batch rather than fail-fast on the first error to allow comprehensive reporting.
- **Outlier Detection**: Using the Interquartile Range (IQR) method (1.5 * IQR) for numerical features. Outliers are flagged with a boolean column, not dropped, to allow human review.

## Feature Engineering
- **Leakage Guard**: Enforced strictly via an `as_of_timestamp` parameter on functions calculating historical features. The test suite explicitly verifies this mechanism.
- **Feature Pipeline**: The `sklearn.Pipeline` is configured to output pandas DataFrames to maintain column names and indices, crucial for interpretation later.

## Dataset Acquisition
- **Traffic Enrichment**: Synthethic OSRM path chosen. A basic time-of-day multiplier is used to simulate traffic conditions without requiring a paid API key.
- **Kaggle Auth**: Uses the single token flow (`KAGGLE_API_TOKEN` env var or `~/.kaggle/access_token`) instead of username/key, in accordance with user direction.

## EDA
- **Visuals**: Static exports of key charts use the specified 'Command Navy' palette (approx `#0B132B` to `#1C2541` for backgrounds, `#3A506B`, `#5BC0BE` for accents).
