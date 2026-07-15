"""
Phase 6 Tests - Vision / Deep Learning Engine

Coverage:
1. OCR test (real, no mocking): creates a simple image with text using
   Pillow, uploads it, runs vision/analyze with mode=ocr, verifies text
   extraction works end-to-end.
2. Classification test (mocked): mocks the classify_image function to
   avoid downloading 100MB+ model weights in CI, verifies the endpoint
   correctly returns classification results.
3. Detection test (mocked): same approach for object detection.
4. Error handling: rejects non-image/PDF datasets, handles missing datasets.
5. Mode filtering: verifies "detect" mode is silently skipped for PDFs.

Database/client/auth fixtures from conftest.py.
"""

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from PIL import Image, ImageDraw, ImageFont


def _create_text_image() -> bytes:
    """Create a PNG image with clear text for OCR testing."""
    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)
    # Use default font (always available, no .ttf needed)
    draw.text((20, 30), "Hello World 2025", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_simple_image() -> bytes:
    """Create a minimal valid PNG image for classification/detection tests."""
    img = Image.new("RGB", (224, 224), color=(128, 200, 100))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 174, 174], fill="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _upload_image(client: AsyncClient, auth_headers: dict, filename: str, content: bytes) -> int:
    """Upload an image file and return its dataset_id."""
    files = {"file": (filename, io.BytesIO(content), "image/png")}
    response = await client.post("/api/v1/data/upload", files=files, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _upload_csv(client: AsyncClient, auth_headers: dict) -> int:
    """Upload a CSV file (used to test rejection of non-image datasets)."""
    csv_content = b"col1,col2\n1,2\n3,4\n"
    files = {"file": ("data.csv", io.BytesIO(csv_content), "text/csv")}
    response = await client.post("/api/v1/data/upload", files=files, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


# ─── OCR Tests (real, no mocking) ──────────────────────────────

@pytest.mark.asyncio
async def test_ocr_extracts_text_from_image(client: AsyncClient, auth_headers: dict):
    """End-to-end OCR: upload image with text, analyze, verify text extracted."""
    image_bytes = _create_text_image()
    dataset_id = await _upload_image(client, auth_headers, "hello.png", image_bytes)

    response = await client.post(
        "/api/v1/vision/analyze",
        json={"dataset_id": dataset_id, "modes": ["ocr"]},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["ocr"] is not None
    assert data["ocr"]["method"] == "Tesseract OCR"
    # Tesseract should find at least part of "Hello World 2025"
    extracted = data["ocr"]["text"].lower()
    assert "hello" in extracted or "world" in extracted or "2025" in extracted
    assert data["ocr"]["char_count"] > 0


@pytest.mark.asyncio
async def test_ocr_on_pdf(client: AsyncClient, auth_headers: dict):
    """OCR on a simple PDF with embedded text."""
    # Create a minimal PDF with text (using pypdf, which we already have)
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    # pypdf can't easily add text to a blank page without reportlab,
    # so we just test that the endpoint handles PDFs gracefully (returns
    # the "no embedded text" message for a blank PDF).
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    files = {"file": ("blank.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_resp = await client.post("/api/v1/data/upload", files=files, headers=auth_headers)
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    response = await client.post(
        "/api/v1/vision/analyze",
        json={"dataset_id": dataset_id, "modes": ["ocr"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["ocr"] is not None


# ─── Classification Tests (mocked) ────────────────────────────

@pytest.mark.asyncio
async def test_classification_returns_top_labels(client: AsyncClient, auth_headers: dict):
    """Classification endpoint returns top-K labels with confidence."""
    image_bytes = _create_simple_image()
    dataset_id = await _upload_image(client, auth_headers, "test_cls.png", image_bytes)

    mock_predictions = [
        {"label": "tabby cat", "confidence": 0.45},
        {"label": "tiger cat", "confidence": 0.30},
        {"label": "Egyptian cat", "confidence": 0.15},
    ]

    with patch("app.services.vision_service.classify_image", return_value=mock_predictions):
        response = await client.post(
            "/api/v1/vision/analyze",
            json={"dataset_id": dataset_id, "modes": ["classify"], "top_k": 3},
            headers=auth_headers,
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["classification"] is not None
    assert len(data["classification"]["predictions"]) == 3
    assert data["classification"]["predictions"][0]["label"] == "tabby cat"
    assert data["classification"]["predictions"][0]["confidence"] == 0.45


# ─── Detection Tests (mocked) ─────────────────────────────────

@pytest.mark.asyncio
async def test_detection_returns_objects_with_bbox(client: AsyncClient, auth_headers: dict):
    """Detection endpoint returns detected objects with bounding boxes."""
    image_bytes = _create_simple_image()
    dataset_id = await _upload_image(client, auth_headers, "test_det.png", image_bytes)

    mock_detections = [
        {"label": "person", "confidence": 0.92, "bbox": [10.0, 20.0, 150.0, 200.0]},
        {"label": "dog", "confidence": 0.75, "bbox": [160.0, 50.0, 220.0, 180.0]},
    ]

    with patch("app.services.vision_service.detect_objects", return_value=mock_detections):
        response = await client.post(
            "/api/v1/vision/analyze",
            json={"dataset_id": dataset_id, "modes": ["detect"]},
            headers=auth_headers,
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["detection"] is not None
    assert len(data["detection"]["detections"]) == 2
    assert data["detection"]["detections"][0]["label"] == "person"
    assert data["detection"]["detections"][0]["bbox"] == [10.0, 20.0, 150.0, 200.0]
    assert data["detection"]["image_size"]["width"] == 224


# ─── All Modes Combined ───────────────────────────────────────

@pytest.mark.asyncio
async def test_all_modes_on_image(client: AsyncClient, auth_headers: dict):
    """Mode 'all' should run classify + detect + ocr on an image."""
    image_bytes = _create_text_image()
    dataset_id = await _upload_image(client, auth_headers, "test_all.png", image_bytes)

    mock_classify = [{"label": "envelope", "confidence": 0.6}]
    mock_detect = [{"label": "book", "confidence": 0.8, "bbox": [0.0, 0.0, 100.0, 50.0]}]

    with patch("app.services.vision_service.classify_image", return_value=mock_classify), \
         patch("app.services.vision_service.detect_objects", return_value=mock_detect):
        response = await client.post(
            "/api/v1/vision/analyze",
            json={"dataset_id": dataset_id, "modes": ["all"]},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["classification"] is not None
    assert data["detection"] is not None
    assert data["ocr"] is not None


# ─── Error Handling ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rejects_non_vision_dataset(client: AsyncClient, auth_headers: dict):
    """CSV datasets should be rejected with 422."""
    dataset_id = await _upload_csv(client, auth_headers)

    response = await client.post(
        "/api/v1/vision/analyze",
        json={"dataset_id": dataset_id, "modes": ["all"]},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert "image" in response.json()["detail"].lower() or "pdf" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_missing_dataset_returns_404(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/vision/analyze",
        json={"dataset_id": 99999, "modes": ["all"]},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invalid_mode_returns_422(client: AsyncClient, auth_headers: dict):
    image_bytes = _create_simple_image()
    dataset_id = await _upload_image(client, auth_headers, "test_bad_mode.png", image_bytes)

    response = await client.post(
        "/api/v1/vision/analyze",
        json={"dataset_id": dataset_id, "modes": ["nonexistent_mode"]},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_detect_mode_skipped_for_pdf(client: AsyncClient, auth_headers: dict):
    """Detection mode should be silently skipped for PDFs (only OCR applies)."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_resp = await client.post("/api/v1/data/upload", files=files, headers=auth_headers)
    dataset_id = upload_resp.json()["id"]

    response = await client.post(
        "/api/v1/vision/analyze",
        json={"dataset_id": dataset_id, "modes": ["detect", "ocr"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # detect should be silently skipped for PDF (not applicable)
    assert data["detection"] is None
    # but OCR should still work
    assert data["ocr"] is not None


@pytest.mark.asyncio
async def test_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/vision/analyze",
        json={"dataset_id": 1, "modes": ["all"]},
    )
    assert response.status_code == 401
