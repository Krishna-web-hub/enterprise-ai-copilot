"""
ML Service — Training, Evaluation, and Prediction

Handles the full lifecycle of a trained model:

    dataset + target column + task type
            │
            ▼
    load data, infer numeric/categorical columns
            │
            ▼
    build preprocessing pipeline (impute + scale/one-hot)
            │
            ▼
    algorithm selection:
        - user specified one  → use it directly
        - user specified none → cross-validate all candidates, keep the best
            │
            ▼
    fit Pipeline(preprocessor, estimator) on a train split
            │
            ▼
    evaluate on a held-out test split → metrics
            │
            ▼
    compute SHAP values on a sample → global feature importance
            │
            ▼
    persist the fitted Pipeline to disk (joblib) + create MLModel record

Why train synchronously inside a thread rather than a background job queue?
See Phase 5 design discussion: datasets are capped at 10k rows (Phase 3's
read limit), so training candidates here finishes in low single-digit
seconds. `asyncio.to_thread` keeps the event loop responsive without
standing up Celery/Redis-backed job infrastructure prematurely.
"""

import asyncio
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    silhouette_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ml.algorithms import (
    SCORING_METRIC,
    AlgorithmSpec,
    get_algorithm,
    get_candidates,
)
from app.ml.preprocessing import (
    build_preprocessor,
    get_output_feature_names,
    infer_column_plan,
)
from app.models.dataset import Dataset
from app.models.ml_model import MLModel
from app.utils.file_readers import read_structured_file

STRUCTURED_TYPES = {"csv", "excel", "json"}
SUPERVISED_TYPES = {"classification", "regression"}
UNSUPERVISED_TYPES = {"clustering", "anomaly_detection"}


class MLServiceError(Exception):
    """Raised for user-facing ML errors (bad column names, unsupported task, etc)."""
    pass


class MLService:
    """Handles ML model training, evaluation, persistence, and prediction."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Training ───────────────────────────────────────────────────

    async def train(
        self,
        dataset: Dataset,
        user_id: int,
        model_type: str,
        target_column: Optional[str],
        algorithm: Optional[str],
        feature_columns: Optional[list[str]],
        name: Optional[str],
    ) -> MLModel:
        """
        Train a new model and persist it. Runs the CPU-bound work in a thread
        so the event loop stays responsive.

        Raises:
            MLServiceError: For any validation or training failure
        """
        if dataset.file_type not in STRUCTURED_TYPES:
            raise MLServiceError(
                f"Cannot train on '{dataset.file_type}' files. "
                "Only structured datasets (CSV, Excel, JSON) support ML training."
            )

        file_path = Path(dataset.file_path)
        if not file_path.exists():
            # Try resolving with upload directory prefix
            from app.core.config import settings
            file_path = Path(settings.upload_path) / dataset.file_path
        if not file_path.exists():
            raise MLServiceError(f"Dataset file not found on disk: {dataset.file_path}")

        # Check file size before loading - reject if too large (>50MB)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 50:
            raise MLServiceError(
                f"Dataset file too large for training: {file_size_mb:.1f} MB. "
                f"Maximum supported is 50 MB. Upload a smaller sample of your data."
            )

        # Also check row count from DB if available
        if dataset.row_count and dataset.row_count > 50_000:
            raise MLServiceError(
                f"Dataset too large for training: {dataset.row_count:,} rows. "
                f"Maximum supported is 50,000 rows. "
                f"Tip: Upload a smaller sample of your data."
            )

        df = read_structured_file(file_path, dataset.file_type)

        row_count = len(df)
        col_count = len(df.columns)

        # Run the actual CPU-bound training in a worker thread with timeout
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    self._train_sync, df, model_type, target_column, algorithm, feature_columns
                ),
                timeout=120.0,  # 2 minute max
            )
        except asyncio.TimeoutError:
            raise MLServiceError(
                f"Training timed out after 2 minutes. "
                f"Your dataset ({row_count:,} rows × {col_count} columns) may be too large "
                f"for the selected algorithm. Try a simpler algorithm or smaller dataset."
            )

        # Persist the fitted pipeline (and, for classification, the label
        # encoder used to map string classes to integers) to disk as one
        # bundle. Both are needed to correctly decode predictions later.
        model_filename = f"{uuid.uuid4().hex}.joblib"
        model_dir = settings.models_path / str(user_id)
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / model_filename
        artifact = {"pipeline": result["pipeline"], "label_encoder": result["label_encoder"]}
        joblib.dump(artifact, model_path)

        # Create the DB record
        ml_model = MLModel(
            user_id=user_id,
            dataset_id=dataset.id,
            name=name or f"{result['algorithm_display_name']} on {dataset.name}",
            model_type=model_type,
            algorithm=result["algorithm_key"],
            target_column=target_column,
            feature_columns=result["feature_columns"],
            metrics=result["metrics"],
            feature_importance=result["feature_importance"],
            model_path=str(model_path),
            parameters=result["parameters"],
            training_duration_seconds=result["training_duration_seconds"],
        )
        self.db.add(ml_model)
        await self.db.flush()
        await self.db.refresh(ml_model)
        return ml_model

    def _train_sync(
        self,
        df: pd.DataFrame,
        model_type: str,
        target_column: Optional[str],
        algorithm: Optional[str],
        feature_columns: Optional[list[str]],
    ) -> dict:
        """
        The synchronous, CPU-bound half of training. Runs inside a thread.

        Returns a dict with: pipeline, algorithm_key, algorithm_display_name,
        feature_columns, metrics, feature_importance, parameters,
        training_duration_seconds.
        """
        start = time.monotonic()

        # ─── Validate columns ───────────────────────────────────────
        if model_type in SUPERVISED_TYPES:
            if not target_column:
                raise MLServiceError(f"target_column is required for {model_type}")
            if target_column not in df.columns:
                raise MLServiceError(
                    f"Target column '{target_column}' not found in dataset. "
                    f"Available columns: {', '.join(df.columns)}"
                )
        elif model_type in UNSUPERVISED_TYPES:
            if target_column:
                raise MLServiceError(
                    f"target_column must not be set for unsupervised task '{model_type}'"
                )
        else:
            raise MLServiceError(f"Unknown model_type: {model_type}")

        if feature_columns:
            missing = [c for c in feature_columns if c not in df.columns]
            if missing:
                raise MLServiceError(f"Feature columns not found in dataset: {', '.join(missing)}")
            resolved_features = feature_columns
        else:
            # Auto-select features: exclude target + problematic columns
            excluded = {target_column} if target_column else set()

            for col in df.columns:
                col_lower = col.lower()
                # Exclude ID-like columns (sequential integers or named 'id')
                if col_lower in ('id', 'index', 'row_id', 'row_number'):
                    excluded.add(col)
                elif col_lower.endswith('id') and col_lower != 'survived':
                    # Check if it looks like a sequential ID
                    if df[col].dtype in ('int64', 'float64') and df[col].nunique() == len(df):
                        excluded.add(col)
                # Exclude very high cardinality text columns (>80% unique = likely names/IDs)
                elif df[col].dtype == 'object':
                    nunique_ratio = df[col].nunique() / max(len(df), 1)
                    if nunique_ratio > 0.8:
                        excluded.add(col)

            resolved_features = [c for c in df.columns if c not in excluded]

        if not resolved_features:
            raise MLServiceError("No feature columns available after excluding the target column")

        # Drop rows where the target is missing (can't train/evaluate on unlabeled rows)
        if model_type in SUPERVISED_TYPES:
            df = df.dropna(subset=[target_column])
            if len(df) < 10:
                raise MLServiceError(
                    "Not enough labeled rows to train a model (need at least 10 after dropping missing targets)."
                )

        X = df[resolved_features]

        plan = infer_column_plan(df, resolved_features)

        if model_type == "classification":
            return self._train_classification(X, df[target_column], plan, algorithm, resolved_features, start)
        elif model_type == "regression":
            return self._train_regression(X, df[target_column], plan, algorithm, resolved_features, start)
        elif model_type == "clustering":
            return self._train_clustering(X, plan, algorithm, resolved_features, start)
        else:  # anomaly_detection
            return self._train_anomaly_detection(X, plan, algorithm, resolved_features, start)

    # ─── Supervised: Classification ────────────────────────────────

    def _train_classification(
        self, X: pd.DataFrame, y: pd.Series, plan, algorithm: Optional[str],
        feature_columns: list[str], start: float,
    ) -> dict:
        # Encode string labels to integers (XGBoost/LightGBM require numeric labels).
        # The fitted encoder is persisted alongside the pipeline (see train())
        # so predictions can be decoded back to the original label strings
        # (e.g. "yes"/"no") instead of leaking raw integer codes to the API.
        label_encoder = None
        if y.dtype == object or str(y.dtype) in ("category", "str"):
            label_encoder = LabelEncoder()
            y_encoded = label_encoder.fit_transform(y)
        else:
            y_encoded = y.to_numpy()

        preprocessor = build_preprocessor(plan)
        spec = self._select_algorithm("classification", algorithm, preprocessor, X, y_encoded)

        pipeline = Pipeline([("preprocessor", preprocessor), ("estimator", spec.factory())])

        # Validate class distribution before training
        unique, counts = np.unique(y_encoded, return_counts=True)
        single_sample_classes = [str(unique[i]) for i in range(len(unique)) if counts[i] < 2]
        if single_sample_classes:
            raise MLServiceError(
                f"Training failed: The target column '{target_column}' has classes with only 1 sample: "
                f"{', '.join(single_sample_classes[:5])}. "
                f"Each class needs at least 2 samples for train/test splitting. "
                f"Please use a larger dataset or pick a different target column."
            )

        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=settings.ML_TEST_SIZE, random_state=42,
            stratify=y_encoded,
        )
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        metrics = {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision_macro": round(float(precision_score(y_test, y_pred, average="macro", zero_division=0)), 4),
            "recall_macro": round(float(recall_score(y_test, y_pred, average="macro", zero_division=0)), 4),
            "f1_macro": round(float(f1_score(y_test, y_pred, average="macro", zero_division=0)), 4),
            "test_samples": len(y_test),
        }

        feature_importance = self._compute_shap_importance(pipeline, X_train)

        elapsed = time.monotonic() - start
        return {
            "pipeline": pipeline,
            "label_encoder": label_encoder,
            "algorithm_key": spec.key,
            "algorithm_display_name": spec.display_name,
            "feature_columns": feature_columns,
            "metrics": metrics,
            "feature_importance": feature_importance,
            "parameters": self._get_estimator_params(pipeline),
            "training_duration_seconds": round(elapsed, 3),
        }

    # ─── Supervised: Regression ─────────────────────────────────────

    def _train_regression(
        self, X: pd.DataFrame, y: pd.Series, plan, algorithm: Optional[str],
        feature_columns: list[str], start: float,
    ) -> dict:
        y_values = y.to_numpy(dtype=float)

        preprocessor = build_preprocessor(plan)
        spec = self._select_algorithm("regression", algorithm, preprocessor, X, y_values)

        pipeline = Pipeline([("preprocessor", preprocessor), ("estimator", spec.factory())])

        X_train, X_test, y_train, y_test = train_test_split(
            X, y_values, test_size=settings.ML_TEST_SIZE, random_state=42
        )
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        metrics = {
            "r2": round(float(r2_score(y_test, y_pred)), 4),
            "rmse": round(rmse, 4),
            "mae": round(float(mean_absolute_error(y_test, y_pred)), 4),
            "test_samples": len(y_test),
        }

        feature_importance = self._compute_shap_importance(pipeline, X_train)

        elapsed = time.monotonic() - start
        return {
            "pipeline": pipeline,
            "label_encoder": None,
            "algorithm_key": spec.key,
            "algorithm_display_name": spec.display_name,
            "feature_columns": feature_columns,
            "metrics": metrics,
            "feature_importance": feature_importance,
            "parameters": self._get_estimator_params(pipeline),
            "training_duration_seconds": round(elapsed, 3),
        }

    # ─── Unsupervised: Clustering ───────────────────────────────────

    def _train_clustering(
        self, X: pd.DataFrame, plan, algorithm: Optional[str],
        feature_columns: list[str], start: float,
    ) -> dict:
        candidates = get_candidates("clustering")
        spec = get_algorithm("clustering", algorithm) if algorithm else candidates[0]

        preprocessor = build_preprocessor(plan)
        pipeline = Pipeline([("preprocessor", preprocessor), ("estimator", spec.factory())])

        # No train/test split for clustering — we fit on all available data
        # since the goal is discovering structure, not predicting held-out labels.
        cluster_labels = pipeline.fit_predict(X)

        X_transformed = pipeline.named_steps["preprocessor"].transform(X)
        n_clusters = len(set(cluster_labels))

        metrics: dict[str, Any] = {"n_clusters": n_clusters, "n_samples": len(X)}
        if n_clusters > 1 and n_clusters < len(X):
            try:
                metrics["silhouette_score"] = round(
                    float(silhouette_score(X_transformed, cluster_labels)), 4
                )
            except Exception:
                pass  # Silhouette can fail on degenerate cases; metrics still useful without it

        estimator = pipeline.named_steps["estimator"]
        if hasattr(estimator, "inertia_"):
            metrics["inertia"] = round(float(estimator.inertia_), 4)

        elapsed = time.monotonic() - start
        return {
            "pipeline": pipeline,
            "label_encoder": None,
            "algorithm_key": spec.key,
            "algorithm_display_name": spec.display_name,
            "feature_columns": feature_columns,
            "metrics": metrics,
            "feature_importance": None,  # Not meaningful for unsupervised clustering
            "parameters": self._get_estimator_params(pipeline),
            "training_duration_seconds": round(elapsed, 3),
        }

    # ─── Unsupervised: Anomaly Detection ────────────────────────────

    def _train_anomaly_detection(
        self, X: pd.DataFrame, plan, algorithm: Optional[str],
        feature_columns: list[str], start: float,
    ) -> dict:
        candidates = get_candidates("anomaly_detection")
        spec = get_algorithm("anomaly_detection", algorithm) if algorithm else candidates[0]

        preprocessor = build_preprocessor(plan)
        pipeline = Pipeline([("preprocessor", preprocessor), ("estimator", spec.factory())])

        # IsolationForest labels: -1 = anomaly, 1 = normal
        predictions = pipeline.fit_predict(X)
        n_anomalies = int(np.sum(predictions == -1))

        metrics = {
            "n_samples": len(X),
            "n_anomalies": n_anomalies,
            "anomaly_rate": round(n_anomalies / len(X), 4) if len(X) > 0 else 0.0,
        }

        elapsed = time.monotonic() - start
        return {
            "pipeline": pipeline,
            "label_encoder": None,
            "algorithm_key": spec.key,
            "algorithm_display_name": spec.display_name,
            "feature_columns": feature_columns,
            "metrics": metrics,
            "feature_importance": None,
            "parameters": self._get_estimator_params(pipeline),
            "training_duration_seconds": round(elapsed, 3),
        }

    # ─── Algorithm Selection ─────────────────────────────────────────

    def _select_algorithm(
        self, model_type: str, algorithm: Optional[str], preprocessor, X: pd.DataFrame, y: np.ndarray,
    ) -> AlgorithmSpec:
        """
        Pick the algorithm to train with.

        If the user specified one, use it directly. Otherwise, cross-validate
        every candidate for this task type and return whichever scores best
        on the configured metric (f1_macro for classification, r2 for
        regression) — this is what satisfies "automatically recommend
        suitable algorithms based on the dataset" rather than a fixed default.
        """
        if algorithm:
            return get_algorithm(model_type, algorithm)

        candidates = get_candidates(model_type)
        scoring = SCORING_METRIC[model_type]
        best_spec = candidates[0]
        best_score = -np.inf

        for spec in candidates:
            try:
                pipeline = Pipeline([("preprocessor", preprocessor), ("estimator", spec.factory())])
                scores = cross_val_score(
                    pipeline, X, y, cv=min(settings.ML_CV_FOLDS, len(X) // 2 or 1),
                    scoring=scoring, error_score="raise",
                )
                mean_score = float(np.mean(scores))
                if mean_score > best_score:
                    best_score = mean_score
                    best_spec = spec
            except Exception:
                # A candidate that fails CV (e.g. too few samples for a fold)
                # is simply skipped rather than aborting the whole bake-off.
                continue

        return best_spec

    # ─── Explainability ──────────────────────────────────────────────

    def _compute_shap_importance(self, pipeline: Pipeline, X_train: pd.DataFrame) -> Optional[dict]:
        """
        Compute global feature importance via SHAP, evaluated once at
        training time (see Phase 5 design discussion for why global vs.
        per-prediction local SHAP).

        Returns a dict of {feature_name: importance_score}, sorted descending,
        or None if SHAP computation isn't supported for this estimator.
        """
        try:
            preprocessor = pipeline.named_steps["preprocessor"]
            estimator = pipeline.named_steps["estimator"]

            # Sample training data to keep SHAP computation fast
            sample = X_train.sample(
                n=min(settings.ML_SHAP_SAMPLE_SIZE, len(X_train)), random_state=42
            )
            X_transformed = preprocessor.transform(sample)
            if hasattr(X_transformed, "toarray"):  # sparse matrix from one-hot encoding
                X_transformed = X_transformed.toarray()

            feature_names = get_output_feature_names(preprocessor)

            import shap
            explainer = shap.Explainer(estimator, X_transformed)
            try:
                # check_additivity=False: tree ensembles (esp. RandomForest) can
                # trip SHAP's internal sum-consistency check due to floating
                # point rounding even when the underlying values are correct.
                # We only use these values for a relative "top N most important
                # features" ranking, not exact attribution math, so disabling
                # the check is safe. Not every explainer type accepts this
                # kwarg (e.g. LinearExplainer for LogisticRegression doesn't),
                # so fall back to calling without it.
                shap_values = explainer(X_transformed, check_additivity=False)
            except TypeError:
                shap_values = explainer(X_transformed)

            values = shap_values.values
            # Multiclass classification: values shape is (n_samples, n_features, n_classes)
            if values.ndim == 3:
                values = np.mean(np.abs(values), axis=2)

            mean_abs_shap = np.mean(np.abs(values), axis=0)

            # Strip sklearn's ColumnTransformer prefix ("numeric__", "categorical__")
            # for readability — users see "tenure_months", not "numeric__tenure_months".
            clean_names = [self._strip_transformer_prefix(n) for n in feature_names]

            importance = dict(zip(clean_names, [round(float(v), 6) for v in mean_abs_shap], strict=False))
            # Sort descending by importance, keep top 20 to avoid huge payloads
            # on datasets with many one-hot-encoded categorical columns
            sorted_importance = dict(
                sorted(importance.items(), key=lambda kv: kv[1], reverse=True)[:20]
            )
            return sorted_importance
        except Exception:
            # SHAP isn't guaranteed to support every estimator/data combination.
            # Fall back to None rather than failing the whole training run —
            # metrics are still useful without an explanation.
            return None

    @staticmethod
    def _strip_transformer_prefix(feature_name: str) -> str:
        """Remove the 'numeric__' / 'categorical__' prefix sklearn adds to ColumnTransformer outputs."""
        for prefix in ("numeric__", "categorical__"):
            if feature_name.startswith(prefix):
                return feature_name[len(prefix):]
        return feature_name

    @staticmethod
    def _get_estimator_params(pipeline: Pipeline) -> dict:
        """Extract the fitted estimator's hyperparameters for storage/display."""
        try:
            params = pipeline.named_steps["estimator"].get_params()
            # Keep only JSON-serializable simple values
            return {
                k: v for k, v in params.items()
                if isinstance(v, str | int | float | bool) or v is None
            }
        except Exception:
            return {}

    # ─── Prediction ───────────────────────────────────────────────────

    async def predict(self, ml_model: MLModel, input_data: dict | list[dict]) -> list[dict]:
        """
        Run predictions using a trained model.

        Args:
            ml_model: The MLModel DB record (used to locate the saved pipeline
                      and stored feature importance for explanations)
            input_data: A single record (dict) or list of records

        Returns:
            A list of {prediction, confidence, explanation} dicts, one per
            input record (a single dict input still returns a one-item list).

        Raises:
            MLServiceError: If the model file is missing or input is malformed
        """
        return await asyncio.to_thread(self._predict_sync, ml_model, input_data)

    def _predict_sync(self, ml_model: MLModel, input_data: dict | list[dict]) -> list[dict]:
        model_path = Path(ml_model.model_path)
        if not model_path.exists():
            raise MLServiceError("The trained model file is missing from storage.")

        artifact = joblib.load(model_path)
        pipeline: Pipeline = artifact["pipeline"]
        label_encoder: Optional[LabelEncoder] = artifact["label_encoder"]

        records = [input_data] if isinstance(input_data, dict) else input_data
        if not records:
            raise MLServiceError("input_data must contain at least one record")

        missing_cols_per_record = []
        for record in records:
            missing = [c for c in ml_model.feature_columns if c not in record]
            if missing:
                missing_cols_per_record.append(missing)

        if missing_cols_per_record:
            raise MLServiceError(
                f"Input data is missing required feature columns: {missing_cols_per_record[0]}"
            )

        input_df = pd.DataFrame(records)[ml_model.feature_columns]

        # Convert empty strings to NaN so imputers can handle missing values
        input_df = input_df.replace('', np.nan)
        # Try to convert numeric-looking columns to numeric types
        for col in input_df.columns:
            input_df[col] = pd.to_numeric(input_df[col], errors='ignore')

        results = []

        if ml_model.model_type == "classification":
            predictions = pipeline.predict(input_df)
            try:
                probabilities = pipeline.predict_proba(input_df)
                confidences = np.max(probabilities, axis=1)
            except Exception:
                confidences = [None] * len(predictions)

            # Decode integer-encoded predictions back to original class labels
            # (e.g. 1 -> "yes") if a label encoder was fitted during training.
            if label_encoder is not None:
                decoded_predictions = label_encoder.inverse_transform(predictions)
            else:
                decoded_predictions = predictions

            for pred, conf in zip(decoded_predictions, confidences, strict=False):
                results.append({
                    "prediction": self._to_native(pred),
                    "confidence": round(float(conf), 4) if conf is not None else None,
                    "explanation": self._build_explanation(ml_model),
                })

        elif ml_model.model_type == "regression":
            predictions = pipeline.predict(input_df)
            for pred in predictions:
                results.append({
                    "prediction": self._to_native(pred),
                    "confidence": None,  # Regression has no natural "confidence" like classification does
                    "explanation": self._build_explanation(ml_model),
                })

        elif ml_model.model_type == "clustering":
            predictions = pipeline.predict(input_df)
            for pred in predictions:
                results.append({
                    "prediction": self._to_native(pred),
                    "confidence": None,
                    "explanation": f"Assigned to cluster {self._to_native(pred)} based on overall similarity "
                                    "to other records in that group.",
                })

        else:  # anomaly_detection
            predictions = pipeline.predict(input_df)
            for pred in predictions:
                is_anomaly = pred == -1
                results.append({
                    "prediction": "anomaly" if is_anomaly else "normal",
                    "confidence": None,
                    "explanation": (
                        "This record deviates significantly from typical patterns in the training data."
                        if is_anomaly
                        else "This record is consistent with typical patterns in the training data."
                    ),
                })

        return results

    @staticmethod
    def _to_native(value) -> Any:
        """Convert numpy scalar types to native Python types for JSON serialization."""
        if isinstance(value, np.generic):
            return value.item()
        return value

    @staticmethod
    def _build_explanation(ml_model: MLModel) -> str:
        """
        Build a natural-language explanation using the model's stored global
        feature importance (computed once at training time via SHAP).
        """
        if not ml_model.feature_importance:
            return "This model does not have feature importance data available."

        top_features = list(ml_model.feature_importance.keys())[:3]
        if not top_features:
            return "This model does not have feature importance data available."

        features_str = ", ".join(top_features)
        return f"This prediction is most influenced by: {features_str} (based on the model's overall learned patterns)."

    # ─── CRUD ──────────────────────────────────────────────────────────

    async def list_models(self, user_id: int, skip: int = 0, limit: int = 20) -> tuple[list[MLModel], int]:
        """List trained models for a user, paginated, newest first."""
        count_result = await self.db.execute(
            select(func.count(MLModel.id)).where(MLModel.user_id == user_id)
        )
        total = count_result.scalar() or 0

        result = await self.db.execute(
            select(MLModel)
            .where(MLModel.user_id == user_id)
            .order_by(MLModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_model(self, model_id: int, user_id: int) -> Optional[MLModel]:
        """Get a single model (must be owned by the user)."""
        result = await self.db.execute(
            select(MLModel).where(MLModel.id == model_id, MLModel.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def delete_model(self, model_id: int, user_id: int) -> bool:
        """Delete a model record and its persisted artifact file."""
        ml_model = await self.get_model(model_id, user_id)
        if not ml_model:
            return False

        model_path = Path(ml_model.model_path)
        if model_path.exists():
            model_path.unlink()

        await self.db.delete(ml_model)
        return True
