from typing import List, Dict, Any, Optional, Union
import pandas as pd
import numpy as np
from pydantic import BaseModel, ValidationError as PydanticValidationError


class ValidationErrorDetail(BaseModel):
    row_index: int
    field: str
    message: str


class ValidationReport(BaseModel):
    total_records: int
    valid_records: int
    error_count: int
    errors: List[ValidationErrorDetail]

    def is_valid(self) -> bool:
        return self.error_count == 0


class DataProcessor:
    """
    Handles missing value imputation, duplicate removal, validation, 
    and outlier detection for Transit datasets.
    """

    def __init__(self, imputation_config: Optional[Dict[str, Any]] = None):
        """
        Args:
            imputation_config: A dictionary specifying imputation strategy per column.
                Example: {'demand_weight': 'median', 'priority': 'unknown'}
        """
        self.imputation_config = imputation_config or {}

    def remove_duplicates(self, df: pd.DataFrame, subset: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Removes duplicate rows based on subset keys (or all columns if None).
        """
        return df.drop_duplicates(subset=subset).copy()

    def impute_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Imputes missing values based on configured strategies.
        Defaults:
            - Numerical: median
            - Categorical/Object: 'unknown'
        """
        df_imputed = df.copy()
        
        for col in df_imputed.columns:
            if df_imputed[col].isnull().any():
                strategy = self.imputation_config.get(col)
                
                is_numeric = pd.api.types.is_numeric_dtype(df_imputed[col])
                
                if not strategy:
                    strategy = 'median' if is_numeric else 'unknown'
                
                if strategy == 'median':
                    if not is_numeric:
                        raise ValueError(f"Cannot use median imputation on non-numeric column: {col}")
                    median_val = df_imputed[col].median()
                    df_imputed[col] = df_imputed[col].fillna(median_val)
                elif strategy == 'mean':
                    if not is_numeric:
                        raise ValueError(f"Cannot use mean imputation on non-numeric column: {col}")
                    mean_val = df_imputed[col].mean()
                    df_imputed[col] = df_imputed[col].fillna(mean_val)
                elif strategy == 'mode':
                    mode_vals = df_imputed[col].mode()
                    if not mode_vals.empty:
                        df_imputed[col] = df_imputed[col].fillna(mode_vals[0])
                elif strategy == 'unknown':
                    df_imputed[col] = df_imputed[col].fillna('unknown')
                else:
                    raise ValueError(f"Unsupported imputation strategy: {strategy} for column {col}")

        return df_imputed

    def flag_outliers(self, df: pd.DataFrame, numeric_cols: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Flags numerical outliers using the IQR method. 
        Creates a boolean column '{col}_is_outlier' for each checked column.
        Does not drop rows.
        """
        df_out = df.copy()
        
        if numeric_cols is None:
            numeric_cols = df_out.select_dtypes(include=[np.number]).columns.tolist()
            
        for col in numeric_cols:
            if col in df_out.columns and pd.api.types.is_numeric_dtype(df_out[col]):
                Q1 = df_out[col].quantile(0.25)
                Q3 = df_out[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outlier_mask = (df_out[col] < lower_bound) | (df_out[col] > upper_bound)
                df_out[f"{col}_is_outlier"] = outlier_mask
                
        return df_out

    def validate_batch(self, df: pd.DataFrame, schema_class: type[BaseModel]) -> ValidationReport:
        """
        Validates a DataFrame against a Pydantic schema class.
        Returns a comprehensive ValidationReport instead of failing fast.
        """
        errors = []
        valid_count = 0
        
        records = df.to_dict(orient='records')
        for i, record in enumerate(records):
            try:
                # Convert NaNs/NaTs to None for Pydantic validation if necessary
                cleaned_record = {
                    k: (None if pd.isna(v) else v) for k, v in record.items()
                }
                schema_class(**cleaned_record)
                valid_count += 1
            except PydanticValidationError as e:
                for err in e.errors():
                    field = ".".join(str(loc) for loc in err['loc'])
                    errors.append(
                        ValidationErrorDetail(
                            row_index=i,
                            field=field,
                            message=err['msg']
                        )
                    )
            except Exception as e:
                errors.append(
                    ValidationErrorDetail(
                        row_index=i,
                        field="root",
                        message=str(e)
                    )
                )

        return ValidationReport(
            total_records=len(df),
            valid_records=valid_count,
            error_count=len(errors),
            errors=errors
        )


def anonymize_coordinates(df: pd.DataFrame, precision: int = 3, lat_cols: List[str] = None, lng_cols: List[str] = None) -> pd.DataFrame:
    """
    Rounds coordinate columns to a specified precision for privacy/export.
    precision=3 equates to roughly neighborhood-level (~110m).
    """
    df_anon = df.copy()
    
    if lat_cols is None:
        lat_cols = [c for c in df_anon.columns if 'lat' in c.lower()]
    if lng_cols is None:
        lng_cols = [c for c in df_anon.columns if 'lng' in c.lower() or 'lon' in c.lower()]
        
    for col in lat_cols + lng_cols:
        if col in df_anon.columns and pd.api.types.is_numeric_dtype(df_anon[col]):
            df_anon[col] = df_anon[col].round(precision)
            
    return df_anon
