"""
Machine Learning Endpoints

Handles ML model training, prediction, and model management.
Supports classification, regression, clustering, and anomaly detection.

Training is synchronous (see Phase 5 design discussion): datasets are capped
at 10k rows (Phase 3's read limit), so a training run — including CV-based
algorithm auto-selection — finishes in low single-digit seconds. It runs in
a worker thread (via asyncio.to_thread inside MLService) so the event loop
stays responsive, but the HTTP response only returns once training and
evaluation are complete. This is reflected in the 201 status code rather
than 202 Accepted, since there's no separate "check job status" endpoint —
the response already contains the finished result.

Routes:
- POST /train           → Train a new ML model on a dataset
- POST /predict         → Get predictions from a trained model
- GET  /models          → List user's trained models
- GET  /models/{id}     → Get model details, metrics, feature importance
- DELETE /models/{id}   → Delete a trained model
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.ml import (
    ModelDetailResponse,
    ModelListResponse,
    PredictRequest,
    PredictResponse,
    TrainRequest,
    TrainResponse,
)
from app.services.data_service import DataService
from app.services.ml_service import MLService, MLServiceError
from app.tasks.ml_tasks import train_model_task

router = APIRouter()


@router.post("/train", status_code=status.HTTP_201_CREATED)
async def train_model(
    request: TrainRequest,
    run_async: bool = Query(False, alias="async", description="Run in background (returns task_id)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Train a machine learning model on a specified dataset.

    The system automatically:
    1. Validates the target/feature columns against the dataset
    2. Preprocesses data (median/mode imputation, scaling, one-hot encoding)
    3. If no algorithm is specified, cross-validates all suitable candidates
       for the task type and keeps the best-scoring one
    4. Trains the model and evaluates it on a held-out split
    5. Computes SHAP-based global feature importance (classification/regression)
    6. Persists the fitted pipeline and returns metrics

    model_type determines whether target_column is required:
    - "classification" / "regression": target_column is required
    - "clustering" / "anomaly_detection": target_column must be omitted
    """
    data_service = DataService(db)
    dataset = await data_service.get_dataset(request.dataset_id, current_user.id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {request.dataset_id} not found",
        )

    # Async mode: dispatch to Celery worker, return task_id immediately
    if run_async:
        try:
            task = train_model_task.delay(
                user_id=current_user.id,
                dataset_id=request.dataset_id,
                model_type=request.model_type,
                target_column=request.target_column,
                algorithm=request.algorithm,
                feature_columns=request.feature_columns,
                name=request.name,
            )
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={"task_id": task.id, "status": "PENDING", "message": "Training started in background. Poll GET /api/v1/tasks/{task_id} for status."},
            )
        except Exception:
            # Redis/Celery not available — fall back to sync
            pass

    # Sync mode (default): train and return immediately
    ml_service = MLService(db)

    try:
        ml_model = await ml_service.train(
            dataset=dataset,
            user_id=current_user.id,
            model_type=request.model_type,
            target_column=request.target_column,
            algorithm=request.algorithm,
            feature_columns=request.feature_columns,
            name=request.name,
        )
    except MLServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return ml_model


@router.post("/predict", response_model=PredictResponse)
async def predict(
    request: PredictRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get predictions from a trained model.

    input_data can be a single record (dict) or a batch (list of dicts).
    Each record must include all of the model's feature_columns.

    Returns predictions with confidence (classification only) and an
    explanation derived from the model's training-time feature importance.
    """
    ml_service = MLService(db)
    ml_model = await ml_service.get_model(request.model_id, current_user.id)

    if not ml_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {request.model_id} not found",
        )

    try:
        predictions = await ml_service.predict(ml_model, request.input_data)
    except MLServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return PredictResponse(
        predictions=predictions,
        model_id=ml_model.id,
        model_name=ml_model.name,
    )


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all trained models for the current user, newest first."""
    ml_service = MLService(db)
    models, total = await ml_service.list_models(current_user.id, skip=skip, limit=limit)
    return ModelListResponse(models=models, total=total)


@router.get("/models/{model_id}", response_model=ModelDetailResponse)
async def get_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get model details including metrics, parameters, and feature importance."""
    ml_service = MLService(db)
    ml_model = await ml_service.get_model(model_id, current_user.id)

    if not ml_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )

    return ml_model


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a trained model and its persisted artifact file."""
    ml_service = MLService(db)
    deleted = await ml_service.delete_model(model_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )


@router.get("/models/{model_id}/sample-input")
async def get_sample_input(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a random sample row from the training dataset to pre-fill prediction form.
    Returns a dict mapping feature_column → sample_value.
    """
    from pathlib import Path
    from app.core.config import settings

    ml_service = MLService(db)
    ml_model = await ml_service.get_model(model_id, current_user.id)

    if not ml_model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Get the dataset
    data_service = DataService(db)
    dataset = await data_service.get_dataset(ml_model.dataset_id, current_user.id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Training dataset not found")

    # Resolve file path
    file_path = Path(dataset.file_path)
    if not file_path.exists():
        file_path = Path(settings.upload_path) / dataset.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file not found on disk")

    # Read a small sample
    import pandas as pd
    try:
        if dataset.file_type == "csv":
            df = pd.read_csv(file_path, nrows=100)
        elif dataset.file_type == "excel":
            df = pd.read_excel(file_path, nrows=100)
        elif dataset.file_type == "json":
            df = pd.read_json(file_path).head(100)
        else:
            df = pd.read_csv(file_path, nrows=100)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not read dataset")

    # Pick a random row and extract only the feature columns
    feature_cols = ml_model.feature_columns or []
    available_cols = [c for c in feature_cols if c in df.columns]

    if not available_cols:
        raise HTTPException(status_code=404, detail="No matching feature columns found in dataset")

    sample_row = df[available_cols].sample(1).iloc[0]

    # Convert to dict with string values (for form input)
    sample_dict = {}
    for col in available_cols:
        val = sample_row[col]
        if pd.isna(val):
            sample_dict[col] = ""
        else:
            sample_dict[col] = str(val)

    return {"sample": sample_dict}
