"""
Algorithm Registry

Defines which estimators are available for each ML task type, and provides
the "automatic algorithm recommendation" behavior described in the product
spec: when the user doesn't pick an algorithm, we cross-validate every
candidate for that task type and keep whichever scores best.

Why a registry instead of one hardcoded default per task?
- The spec explicitly asks the platform to "automatically recommend suitable
  algorithms based on the dataset" — a single hardcoded choice wouldn't
  satisfy that, it would just be a default.
- Keeping this as a plain dict of factories (not fitted instances) means
  each CV fold gets a fresh, unfitted estimator — reusing a fitted instance
  across folds would leak information between folds.

Scoring metric per task type:
- Classification: F1 (macro) — robust to class imbalance, which is common in
  business datasets (e.g. churn is usually the minority class)
- Regression: R² — standard, interpretable "fraction of variance explained"
- Clustering / anomaly detection: no CV bake-off (unsupervised, no ground
  truth label to score against) — these use one fixed, well-established
  algorithm each (KMeans, IsolationForest)
"""

from collections.abc import Callable
from dataclasses import dataclass

from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.cluster import KMeans
from sklearn.ensemble import (
    IsolationForest,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from xgboost import XGBClassifier, XGBRegressor


@dataclass
class AlgorithmSpec:
    """Describes one candidate algorithm for a task type."""
    key: str  # stored in MLModel.algorithm, e.g. "random_forest"
    display_name: str
    factory: Callable  # zero-arg callable returning a fresh, unfitted estimator


# ─── Classification candidates ─────────────────────────────────
CLASSIFICATION_ALGORITHMS: list[AlgorithmSpec] = [
    AlgorithmSpec("logistic_regression", "Logistic Regression",
                  lambda: LogisticRegression(max_iter=1000, random_state=42)),
    AlgorithmSpec("random_forest", "Random Forest",
                  lambda: RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)),
    AlgorithmSpec("xgboost", "XGBoost",
                  lambda: XGBClassifier(random_state=42, eval_metric="logloss", verbosity=0)),
    AlgorithmSpec("lightgbm", "LightGBM",
                  lambda: LGBMClassifier(random_state=42, verbosity=-1)),
]

# ─── Regression candidates ─────────────────────────────────────
REGRESSION_ALGORITHMS: list[AlgorithmSpec] = [
    AlgorithmSpec("linear_regression", "Linear Regression",
                  lambda: LinearRegression()),
    AlgorithmSpec("random_forest", "Random Forest",
                  lambda: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)),
    AlgorithmSpec("xgboost", "XGBoost",
                  lambda: XGBRegressor(random_state=42, verbosity=0)),
    AlgorithmSpec("lightgbm", "LightGBM",
                  lambda: LGBMRegressor(random_state=42, verbosity=-1)),
]

# ─── Clustering (unsupervised — one fixed algorithm) ──────────
CLUSTERING_ALGORITHMS: list[AlgorithmSpec] = [
    AlgorithmSpec("kmeans", "K-Means",
                  lambda: KMeans(n_clusters=3, random_state=42, n_init=10)),
]

# ─── Anomaly detection (unsupervised — one fixed algorithm) ───
ANOMALY_DETECTION_ALGORITHMS: list[AlgorithmSpec] = [
    AlgorithmSpec("isolation_forest", "Isolation Forest",
                  lambda: IsolationForest(contamination=0.1, random_state=42, n_jobs=-1)),
]

_REGISTRY: dict[str, list[AlgorithmSpec]] = {
    "classification": CLASSIFICATION_ALGORITHMS,
    "regression": REGRESSION_ALGORITHMS,
    "clustering": CLUSTERING_ALGORITHMS,
    "anomaly_detection": ANOMALY_DETECTION_ALGORITHMS,
}

# The CV scoring metric used to compare candidates within a task type.
SCORING_METRIC: dict[str, str] = {
    "classification": "f1_macro",
    "regression": "r2",
}


def get_candidates(model_type: str) -> list[AlgorithmSpec]:
    """
    Get all candidate algorithms for a task type.

    Raises:
        ValueError: If model_type is not a recognized task type
    """
    if model_type not in _REGISTRY:
        valid = ", ".join(_REGISTRY.keys())
        raise ValueError(f"Unknown model_type '{model_type}'. Must be one of: {valid}")
    return _REGISTRY[model_type]


def get_algorithm(model_type: str, algorithm_key: str) -> AlgorithmSpec:
    """
    Get a specific algorithm by key within a task type (used when the user
    explicitly requests an algorithm instead of relying on auto-selection).

    Raises:
        ValueError: If model_type or algorithm_key is not recognized
    """
    candidates = get_candidates(model_type)
    for spec in candidates:
        if spec.key == algorithm_key:
            return spec

    valid_keys = ", ".join(c.key for c in candidates)
    raise ValueError(
        f"Unknown algorithm '{algorithm_key}' for model_type '{model_type}'. "
        f"Available: {valid_keys}"
    )
