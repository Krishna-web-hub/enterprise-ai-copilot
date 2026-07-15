"""
Vision Analysis Schemas (Pydantic)

Request/response contracts for the deep learning vision endpoint.
"""

from typing import Optional

from pydantic import BaseModel, Field


class VisionAnalyzeRequest(BaseModel):
    """Request to analyze an image or PDF dataset with deep learning models."""
    dataset_id: int
    modes: list[str] = Field(
        default=["all"],
        description='Analysis modes to run. Options: "classify", "detect", "ocr", "all"',
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Top-K classification predictions")
    confidence_threshold: float = Field(
        default=0.5, ge=0.1, le=1.0,
        description="Minimum confidence for object detection results",
    )


class ClassificationPrediction(BaseModel):
    label: str
    confidence: float


class ClassificationResult(BaseModel):
    model: str
    predictions: list[ClassificationPrediction]


class DetectionItem(BaseModel):
    label: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]


class ImageSize(BaseModel):
    width: int
    height: int


class DetectionResult(BaseModel):
    model: str
    detections: list[DetectionItem]
    image_size: ImageSize


class OCRResult(BaseModel):
    method: str
    text: str
    char_count: int
    mean_confidence: Optional[float] = None
    word_count: Optional[int] = None


class VisionAnalyzeResponse(BaseModel):
    """
    Response containing results from requested vision analysis modes.
    Only the modes that were actually run will have non-null values.
    """
    dataset_id: int
    dataset_name: str
    file_type: str
    classification: Optional[ClassificationResult] = None
    detection: Optional[DetectionResult] = None
    ocr: Optional[OCRResult] = None
