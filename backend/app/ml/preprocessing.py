"""
Preprocessing Pipeline Builder

Builds a scikit-learn ColumnTransformer that handles the two broad column
kinds present in any uploaded dataset:
- Numeric columns: median imputation (robust to outliers) + standard scaling
- Categorical/text columns: most-frequent imputation + one-hot encoding

Why build this from dtype instead of asking the user to configure it?
- The platform's whole pitch is "upload data, ask questions" — forcing users
  to manually specify preprocessing per column defeats that. Reasonable
  defaults based on inferred dtype cover the vast majority of business data.

Why bundle preprocessing INTO the persisted model (as one sklearn Pipeline)
rather than preprocessing once and saving a plain estimator?
- Predictions later arrive as raw column values (e.g. {"city": "Boston"}).
  If the preprocessing logic isn't saved alongside the model, there's no
  guarantee predict-time transformation matches train-time transformation
  (e.g. the one-hot encoder's learned categories, the scaler's learned
  mean/std). A single fitted Pipeline object guarantees this by construction.
"""

from dataclasses import dataclass

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Pandas dtype substrings that indicate a numeric column.
# Matched with substring containment against str(dtype), so this covers
# int8/16/32/64, uint*, float32/64, etc.
NUMERIC_DTYPE_MARKERS = ("int", "float", "uint")


@dataclass
class ColumnPlan:
    """Which columns are treated as numeric vs. categorical for preprocessing."""
    numeric_columns: list[str]
    categorical_columns: list[str]


def infer_column_plan(df: pd.DataFrame, feature_columns: list[str]) -> ColumnPlan:
    """
    Split feature columns into numeric vs. categorical based on pandas dtype.

    Args:
        df: The full dataframe (used only to inspect dtypes)
        feature_columns: The subset of columns to use as model features

    Returns:
        A ColumnPlan listing which of feature_columns are numeric/categorical
    """
    numeric_columns = []
    categorical_columns = []

    for col in feature_columns:
        dtype_str = str(df[col].dtype).lower()
        if any(marker in dtype_str for marker in NUMERIC_DTYPE_MARKERS):
            numeric_columns.append(col)
        else:
            categorical_columns.append(col)

    return ColumnPlan(numeric_columns=numeric_columns, categorical_columns=categorical_columns)


def build_preprocessor(plan: ColumnPlan) -> ColumnTransformer:
    """
    Build a ColumnTransformer that preprocesses numeric and categorical
    columns appropriately, ready to be the first step of a training Pipeline.

    Numeric pipeline: median imputation → standard scaling
    Categorical pipeline: most-frequent imputation → one-hot encoding
        (unknown categories at predict time are ignored rather than raising,
        since a user's future prediction input may contain a category value
        that never appeared during training)
    """
    transformers = []

    if plan.numeric_columns:
        numeric_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])
        transformers.append(("numeric", numeric_pipeline, plan.numeric_columns))

    if plan.categorical_columns:
        categorical_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ])
        transformers.append(("categorical", categorical_pipeline, plan.categorical_columns))

    if not transformers:
        raise ValueError("No usable feature columns found (neither numeric nor categorical).")

    return ColumnTransformer(transformers=transformers, remainder="drop")


def get_output_feature_names(preprocessor: ColumnTransformer) -> list[str]:
    """
    Get human-readable feature names after preprocessing (e.g. one-hot
    encoding turns "city" into "city_Boston", "city_Chicago", ...).

    Used to map SHAP values (computed on the transformed feature space)
    back to meaningful names for the explanation.
    """
    try:
        return list(preprocessor.get_feature_names_out())
    except Exception:
        # Fallback for edge cases where sklearn can't derive names
        n_features = preprocessor.transform(preprocessor.feature_names_in_[:1]).shape[1] if hasattr(
            preprocessor, "feature_names_in_"
        ) else 0
        return [f"feature_{i}" for i in range(n_features)]
