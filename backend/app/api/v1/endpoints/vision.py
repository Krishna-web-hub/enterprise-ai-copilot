"""
Vision / Deep Learning Endpoints

Runs pretrained deep learning inference on uploaded image and PDF datasets.

This is an inference-only endpoint — unlike /ml/train, there's no
user-provided training data for vision models. Instead, pretrained models
(ResNet18 for classification, Faster R-CNN for detection, Tesseract for
OCR) analyze the uploaded file and return structured results.

Routes:
- POST /analyze → Run classification, detection, and/or OCR on an image/PDF dataset
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.vision import VisionAnalyzeRequest, VisionAnalyzeResponse
from app.services.data_service import DataService
from app.services.vision_service import VisionService, VisionServiceError

router = APIRouter()


@router.post("/analyze", response_model=VisionAnalyzeResponse)
async def analyze_image(
    request: VisionAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze an image or PDF dataset with deep learning models.

    Available modes:
    - "classify": Image classification (ResNet18, ImageNet 1000 classes)
    - "detect": Object detection (Faster R-CNN, COCO 80 classes, bounding boxes)
    - "ocr": Text extraction (Tesseract OCR for images, pypdf for PDFs)
    - "all": Run all modes applicable to the file type

    Note: Classification and detection are only applicable to image files.
    OCR works on both images and PDFs.

    First call may take a few seconds while model weights are loaded into
    memory. Subsequent calls are fast (models are cached as singletons).
    """
    data_service = DataService(db)
    dataset = await data_service.get_dataset(request.dataset_id, current_user.id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {request.dataset_id} not found",
        )

    vision_service = VisionService()

    try:
        results = await vision_service.analyze(
            dataset=dataset,
            modes=request.modes,
            top_k=request.top_k,
            confidence_threshold=request.confidence_threshold,
        )
    except VisionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return VisionAnalyzeResponse(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        file_type=dataset.file_type,
        classification=results.get("classification"),
        detection=results.get("detection"),
        ocr=results.get("ocr"),
    )
