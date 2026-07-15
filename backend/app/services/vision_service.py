"""
Vision Service — Orchestrates Deep Learning Inference

Takes a Dataset record (must be image or PDF type), determines which
analysis capabilities to run, and returns structured results.

Analysis modes:
- "classify": Run image classification (top-N ImageNet labels with confidence)
- "detect": Run object detection (COCO classes, bounding boxes)
- "ocr": Extract text from images or PDFs

The user can request one or more modes in a single call, or request "all"
to run everything applicable.

Why a service layer rather than calling vision_models/ocr directly from
the endpoint?
- Same reason as every other service: reusable by future agents (the Vision
  Agent in Phase 8 will call VisionService.analyze() as a tool), testable
  in isolation, and keeps the endpoint handler thin.
- Centralizes the "which modes are applicable to which file type" logic in
  one place (e.g. detection on PDFs doesn't make sense — only OCR does).
"""

import asyncio
from pathlib import Path
from typing import Any, Optional

from PIL import Image

from app.dl.ocr import (
    extract_text_from_pdf,
    get_ocr_with_confidence,
)
from app.dl.vision_models import classify_image, detect_objects
from app.models.dataset import Dataset

# File types that support each analysis mode
IMAGE_TYPES = {"image"}
PDF_TYPES = {"pdf"}
VISION_TYPES = IMAGE_TYPES | PDF_TYPES  # All types that the vision service can handle

# Which analysis modes apply to which file types
MODE_APPLICABILITY = {
    "classify": IMAGE_TYPES,  # Only images — classifying a PDF page doesn't make sense
    "detect": IMAGE_TYPES,    # Only images — detection needs pixel data
    "ocr": IMAGE_TYPES | PDF_TYPES,  # Both images and PDFs contain text to extract
}

VALID_MODES = set(MODE_APPLICABILITY.keys())


class VisionServiceError(Exception):
    """Raised for user-facing vision analysis errors."""
    pass


class VisionService:
    """Orchestrates deep learning inference on image/PDF datasets."""

    async def analyze(
        self,
        dataset: Dataset,
        modes: list[str],
        top_k: int = 5,
        confidence_threshold: float = 0.5,
    ) -> dict[str, Any]:
        """
        Run one or more vision analysis modes on a dataset's file.

        Args:
            dataset: The Dataset record (must be image or PDF type)
            modes: List of analysis modes to run. Options: "classify", "detect", "ocr", "all"
            top_k: Number of top classification predictions to return
            confidence_threshold: Minimum confidence for object detection results

        Returns:
            Dict with keys matching the requested modes, each containing
            the analysis results for that mode.

        Raises:
            VisionServiceError: If the dataset isn't an image/PDF, or the file is missing
        """
        if dataset.file_type not in VISION_TYPES:
            raise VisionServiceError(
                f"Vision analysis is only available for image and PDF files, "
                f"not '{dataset.file_type}' files."
            )

        file_path = Path(dataset.file_path)
        if not file_path.exists():
            from app.core.config import settings
            file_path = Path(settings.upload_path) / dataset.file_path
        if not file_path.exists():
            raise VisionServiceError(f"Dataset file not found on disk: {dataset.file_path}")

        # Expand "all" into applicable modes for this file type
        resolved_modes = self._resolve_modes(modes, dataset.file_type)

        # Run the analysis in a thread to keep the event loop free
        # (model inference is CPU-bound)
        return await asyncio.to_thread(
            self._analyze_sync, file_path, dataset.file_type, resolved_modes,
            top_k, confidence_threshold,
        )

    def _analyze_sync(
        self,
        file_path: Path,
        file_type: str,
        modes: list[str],
        top_k: int,
        confidence_threshold: float,
    ) -> dict[str, Any]:
        """Synchronous analysis worker (runs in a thread)."""
        results: dict[str, Any] = {}

        # Load image once if needed by classification or detection
        image: Optional[Image.Image] = None
        if file_type in IMAGE_TYPES and ("classify" in modes or "detect" in modes):
            image = Image.open(file_path)

        if "classify" in modes and image is not None:
            results["classification"] = self._run_classification(image, top_k)

        if "detect" in modes and image is not None:
            results["detection"] = self._run_detection(image, confidence_threshold)

        if "ocr" in modes:
            results["ocr"] = self._run_ocr(file_path, file_type)

        return results

    @staticmethod
    def _run_classification(image: Image.Image, top_k: int) -> dict:
        """Run image classification and format results."""
        predictions = classify_image(image, top_k=top_k)
        return {
            "model": "ResNet18 (ImageNet)",
            "predictions": predictions,
        }

    @staticmethod
    def _run_detection(image: Image.Image, confidence_threshold: float) -> dict:
        """Run object detection and format results."""
        detections = detect_objects(image, confidence_threshold=confidence_threshold)
        return {
            "model": "Faster R-CNN (COCO)",
            "detections": detections,
            "image_size": {"width": image.width, "height": image.height},
        }

    @staticmethod
    def _run_ocr(file_path: Path, file_type: str) -> dict:
        """Run OCR (text extraction) and format results."""
        if file_type in PDF_TYPES:
            text = extract_text_from_pdf(file_path)
            return {
                "method": "pypdf (embedded text extraction)",
                "text": text,
                "char_count": len(text),
            }
        else:
            # Image — use OCR with confidence data
            ocr_result = get_ocr_with_confidence(file_path)
            return {
                "method": "Tesseract OCR",
                "text": ocr_result["text"],
                "char_count": len(ocr_result["text"]),
                "mean_confidence": ocr_result["mean_confidence"],
                "word_count": len(ocr_result["text"].split()) if ocr_result["text"] else 0,
            }

    @staticmethod
    def _resolve_modes(modes: list[str], file_type: str) -> list[str]:
        """
        Resolve requested modes into the actual list to run, filtering out
        modes that don't apply to this file type and expanding "all".
        """
        if "all" in modes:
            # Return all modes applicable to this file type
            return [
                mode for mode, applicable_types in MODE_APPLICABILITY.items()
                if file_type in applicable_types
            ]

        resolved = []
        for mode in modes:
            if mode not in VALID_MODES:
                raise VisionServiceError(
                    f"Unknown analysis mode '{mode}'. Valid modes: {', '.join(sorted(VALID_MODES))}, all"
                )
            if file_type in MODE_APPLICABILITY[mode]:
                resolved.append(mode)
            # Silently skip modes that don't apply (e.g. "detect" on a PDF)
            # rather than erroring — "all" already filters, and explicit requests
            # for inapplicable modes are harmless to skip.

        if not resolved:
            raise VisionServiceError(
                f"None of the requested modes ({', '.join(modes)}) are applicable "
                f"to '{file_type}' files."
            )

        return resolved
