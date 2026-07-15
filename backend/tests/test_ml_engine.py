"""
Phase 5 Tests - ML Engine (Training, Prediction, Algorithm Auto-Selection)

Coverage:
1. Full endpoint integration tests: upload a dataset, train models of each
   type (classification, regression, clustering, anomaly_detection), verify
   metrics/feature importance are present, run predictions, list/get/delete.
2. Error handling: bad target column, unsupported task/target combination,
   missing dataset, missing model.

Training uses small synthetic datasets (100-200 rows) so tests run quickly —
real CV bake-offs across 4 algorithms complete in a couple seconds at this scale.

Database/client/auth fixtures come from conftest.py.
"""

import io
import warnings

import numpy as np
import pandas as pd
import pytest
from httpx import AsyncClient

warnings.filterwarnings("ignore")


def _make_classification_csv(n: int = 150) -> str:
    """Synthetic churn-like dataset: tenure_months, monthly_charges, contract_type -> churn."""
    rng = np.random.RandomState(42)
    tenure = rng.randint(1, 72, n)
    charges = rng.uniform(20, 120, n)
    contract = rng.choice(["month-to-month", "one-year", "two-year"], n)
    churn_prob = 1 / (1 + np.exp(-(0.05 * (30 - tenure) + 0.02 * (charges - 70))))
    churn = (rng.random(n) < churn_prob).astype(int)
    churn_labels = np.where(churn == 1, "yes", "no")

    df = pd.DataFrame({
        "tenure_months": tenure,
        "monthly_charges": charges,
        "contract_type": contract,
        "churn": churn_labels,
    })
    return df.to_csv(index=False)


def _make_regression_csv(n: int = 150) -> str:
    """Synthetic dataset: tenure_months, contract_type -> monthly_charges."""
    rng = np.random.RandomState(42)
    tenure = rng.randint(1, 72, n)
    contract = rng.choice(["month-to-month", "one-year", "two-year"], n)
    charges = 50 + 0.5 * tenure + rng.normal(0, 5, n)

    df = pd.DataFrame({
        "tenure_months": tenure,
        "contract_type": contract,
        "monthly_charges": charges,
    })
    return df.to_csv(index=False)


async def _upload_csv(client: AsyncClient, auth_headers: dict, filename: str, csv_content: str) -> int:
    """Helper: upload a CSV and return its dataset_id."""
    files = {"file": (filename, io.BytesIO(csv_content.encode()), "text/csv")}
    response = await client.post("/api/v1/data/upload", files=files, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


# ─── Classification ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_train_classification_auto_select(client: AsyncClient, auth_headers: dict):
    """Training with no algorithm specified should auto-select via CV bake-off."""
    dataset_id = await _upload_csv(client, auth_headers, "churn.csv", _make_classification_csv())

    response = await client.post(
        "/api/v1/ml/train",
        json={"dataset_id": dataset_id, "model_type": "classification", "target_column": "churn"},
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["model_type"] == "classification"
    assert data["algorithm"] in ("logistic_regression", "random_forest", "xgboost", "lightgbm")
    assert "accuracy" in data["metrics"]
    assert "f1_macro" in data["metrics"]
    assert data["feature_importance"] is not None
    assert data["training_duration_seconds"] is not None


@pytest.mark.asyncio
async def test_train_classification_explicit_algorithm(client: AsyncClient, auth_headers: dict):
    """Training with an explicit algorithm should use exactly that one, skipping the bake-off."""
    dataset_id = await _upload_csv(client, auth_headers, "churn2.csv", _make_classification_csv())

    response = await client.post(
        "/api/v1/ml/train",
        json={
            "dataset_id": dataset_id, "model_type": "classification",
            "target_column": "churn", "algorithm": "random_forest",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["algorithm"] == "random_forest"


@pytest.mark.asyncio
async def test_predict_classification_returns_decoded_label(client: AsyncClient, auth_headers: dict):
    """Predictions must return original string labels (e.g. 'yes'/'no'), not encoded integers."""
    dataset_id = await _upload_csv(client, auth_headers, "churn3.csv", _make_classification_csv())

    train_response = await client.post(
        "/api/v1/ml/train",
        json={"dataset_id": dataset_id, "model_type": "classification", "target_column": "churn"},
        headers=auth_headers,
    )
    model_id = train_response.json()["id"]

    predict_response = await client.post(
        "/api/v1/ml/predict",
        json={
            "model_id": model_id,
            "input_data": {"tenure_months": 5, "monthly_charges": 100.0, "contract_type": "month-to-month"},
        },
        headers=auth_headers,
    )

    assert predict_response.status_code == 200, predict_response.text
    data = predict_response.json()
    assert len(data["predictions"]) == 1
    pred = data["predictions"][0]
    assert pred["prediction"] in ("yes", "no")  # decoded label, not 0/1
    assert pred["confidence"] is not None
    assert 0 <= pred["confidence"] <= 1
    assert len(pred["explanation"]) > 0


@pytest.mark.asyncio
async def test_predict_batch(client: AsyncClient, auth_headers: dict):
    """Predict endpoint should support a batch (list) of input records."""
    dataset_id = await _upload_csv(client, auth_headers, "churn4.csv", _make_classification_csv())
    train_response = await client.post(
        "/api/v1/ml/train",
        json={"dataset_id": dataset_id, "model_type": "classification", "target_column": "churn"},
        headers=auth_headers,
    )
    model_id = train_response.json()["id"]

    predict_response = await client.post(
        "/api/v1/ml/predict",
        json={
            "model_id": model_id,
            "input_data": [
                {"tenure_months": 5, "monthly_charges": 100.0, "contract_type": "month-to-month"},
                {"tenure_months": 60, "monthly_charges": 30.0, "contract_type": "two-year"},
            ],
        },
        headers=auth_headers,
    )

    assert predict_response.status_code == 200
    assert len(predict_response.json()["predictions"]) == 2


# ─── Regression ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_train_regression(client: AsyncClient, auth_headers: dict):
    dataset_id = await _upload_csv(client, auth_headers, "pricing.csv", _make_regression_csv())

    response = await client.post(
        "/api/v1/ml/train",
        json={
            "dataset_id": dataset_id, "model_type": "regression",
            "target_column": "monthly_charges", "algorithm": "linear_regression",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["algorithm"] == "linear_regression"
    assert "r2" in data["metrics"]
    assert "rmse" in data["metrics"]
    assert "mae" in data["metrics"]


@pytest.mark.asyncio
async def test_predict_regression_has_no_confidence(client: AsyncClient, auth_headers: dict):
    """Regression predictions have no natural 'confidence' — should be None."""
    dataset_id = await _upload_csv(client, auth_headers, "pricing2.csv", _make_regression_csv())
    train_response = await client.post(
        "/api/v1/ml/train",
        json={"dataset_id": dataset_id, "model_type": "regression", "target_column": "monthly_charges"},
        headers=auth_headers,
    )
    model_id = train_response.json()["id"]

    predict_response = await client.post(
        "/api/v1/ml/predict",
        json={
            "model_id": model_id,
            "input_data": {"tenure_months": 24, "contract_type": "one-year"},
        },
        headers=auth_headers,
    )

    assert predict_response.status_code == 200
    pred = predict_response.json()["predictions"][0]
    assert isinstance(pred["prediction"], int | float)
    assert pred["confidence"] is None


# ─── Unsupervised: Clustering & Anomaly Detection ──────────────

@pytest.mark.asyncio
async def test_train_clustering(client: AsyncClient, auth_headers: dict):
    dataset_id = await _upload_csv(client, auth_headers, "customers.csv", _make_regression_csv())

    response = await client.post(
        "/api/v1/ml/train",
        json={
            "dataset_id": dataset_id, "model_type": "clustering",
            "feature_columns": ["tenure_months", "monthly_charges"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["algorithm"] == "kmeans"
    assert "n_clusters" in data["metrics"]
    # Clustering has no supervised target, so feature_importance should be absent
    assert data["feature_importance"] is None


@pytest.mark.asyncio
async def test_train_clustering_rejects_target_column(client: AsyncClient, auth_headers: dict):
    """Unsupervised tasks must reject a target_column if one is provided."""
    dataset_id = await _upload_csv(client, auth_headers, "customers2.csv", _make_regression_csv())

    response = await client.post(
        "/api/v1/ml/train",
        json={
            "dataset_id": dataset_id, "model_type": "clustering",
            "target_column": "monthly_charges",  # invalid for clustering
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_train_anomaly_detection(client: AsyncClient, auth_headers: dict):
    dataset_id = await _upload_csv(client, auth_headers, "transactions.csv", _make_regression_csv())

    response = await client.post(
        "/api/v1/ml/train",
        json={
            "dataset_id": dataset_id, "model_type": "anomaly_detection",
            "feature_columns": ["tenure_months", "monthly_charges"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["algorithm"] == "isolation_forest"
    assert "n_anomalies" in data["metrics"]


@pytest.mark.asyncio
async def test_predict_anomaly_detection(client: AsyncClient, auth_headers: dict):
    dataset_id = await _upload_csv(client, auth_headers, "transactions2.csv", _make_regression_csv())
    train_response = await client.post(
        "/api/v1/ml/train",
        json={
            "dataset_id": dataset_id, "model_type": "anomaly_detection",
            "feature_columns": ["tenure_months", "monthly_charges"],
        },
        headers=auth_headers,
    )
    model_id = train_response.json()["id"]

    predict_response = await client.post(
        "/api/v1/ml/predict",
        json={"model_id": model_id, "input_data": {"tenure_months": 30, "monthly_charges": 65.0}},
        headers=auth_headers,
    )

    assert predict_response.status_code == 200
    pred = predict_response.json()["predictions"][0]
    assert pred["prediction"] in ("anomaly", "normal")


# ─── CRUD ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_models(client: AsyncClient, auth_headers: dict):
    dataset_id = await _upload_csv(client, auth_headers, "list_test.csv", _make_classification_csv())
    await client.post(
        "/api/v1/ml/train",
        json={"dataset_id": dataset_id, "model_type": "classification", "target_column": "churn"},
        headers=auth_headers,
    )

    response = await client.get("/api/v1/ml/models", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["models"]) == 1


@pytest.mark.asyncio
async def test_get_model_detail(client: AsyncClient, auth_headers: dict):
    dataset_id = await _upload_csv(client, auth_headers, "detail_test.csv", _make_classification_csv())
    train_response = await client.post(
        "/api/v1/ml/train",
        json={"dataset_id": dataset_id, "model_type": "classification", "target_column": "churn"},
        headers=auth_headers,
    )
    model_id = train_response.json()["id"]

    response = await client.get(f"/api/v1/ml/models/{model_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == model_id
    assert data["target_column"] == "churn"
    assert set(data["feature_columns"]) == {"tenure_months", "monthly_charges", "contract_type"}


@pytest.mark.asyncio
async def test_get_nonexistent_model(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/ml/models/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_model(client: AsyncClient, auth_headers: dict):
    dataset_id = await _upload_csv(client, auth_headers, "delete_test.csv", _make_classification_csv())
    train_response = await client.post(
        "/api/v1/ml/train",
        json={"dataset_id": dataset_id, "model_type": "classification", "target_column": "churn"},
        headers=auth_headers,
    )
    model_id = train_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/ml/models/{model_id}", headers=auth_headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/ml/models/{model_id}", headers=auth_headers)
    assert get_response.status_code == 404


# ─── Error Handling ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_train_missing_dataset(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/ml/train",
        json={"dataset_id": 99999, "model_type": "classification", "target_column": "churn"},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_train_bad_target_column(client: AsyncClient, auth_headers: dict):
    dataset_id = await _upload_csv(client, auth_headers, "bad_target.csv", _make_classification_csv())

    response = await client.post(
        "/api/v1/ml/train",
        json={"dataset_id": dataset_id, "model_type": "classification", "target_column": "does_not_exist"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_train_classification_missing_target_column(client: AsyncClient, auth_headers: dict):
    """Supervised task types must reject a missing target_column."""
    dataset_id = await _upload_csv(client, auth_headers, "no_target.csv", _make_classification_csv())

    response = await client.post(
        "/api/v1/ml/train",
        json={"dataset_id": dataset_id, "model_type": "classification"},  # no target_column
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_predict_missing_model(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/ml/predict",
        json={"model_id": 99999, "input_data": {"x": 1}},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_predict_missing_feature_column(client: AsyncClient, auth_headers: dict):
    dataset_id = await _upload_csv(client, auth_headers, "missing_feat.csv", _make_classification_csv())
    train_response = await client.post(
        "/api/v1/ml/train",
        json={"dataset_id": dataset_id, "model_type": "classification", "target_column": "churn"},
        headers=auth_headers,
    )
    model_id = train_response.json()["id"]

    # Omit "contract_type", a required feature column
    response = await client.post(
        "/api/v1/ml/predict",
        json={"model_id": model_id, "input_data": {"tenure_months": 5, "monthly_charges": 100.0}},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_train_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/ml/train",
        json={"dataset_id": 1, "model_type": "classification", "target_column": "x"},
    )
    assert response.status_code == 401
