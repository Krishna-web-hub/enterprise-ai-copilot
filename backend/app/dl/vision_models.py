"""
Vision Model Loaders

Provides lazy-loaded singletons for pretrained torchvision models.
Models are loaded once on first use and cached for subsequent requests.

Why lazy loading?
- Loading a 100+ MB model takes 1-2 seconds. Doing it at module import
  time would slow down app startup (and any test that imports the app) by
  seconds even when the vision endpoint is never used in that session.
- Lazy loading means the first request to /vision/analyze pays the load
  cost, all subsequent requests are instant.

Why singletons instead of per-request loading?
- These models are read-only (inference mode). No state changes between
  requests, so sharing one instance is safe and avoids the OOM risk of
  loading multiple 100MB+ copies into a 7GB-RAM system.
"""

from typing import Optional

import torch
from PIL import Image
from torchvision import models, transforms
from torchvision.models.detection import (
    FasterRCNN_ResNet50_FPN_Weights,
    fasterrcnn_resnet50_fpn,
)

# ─── ImageNet Class Labels ─────────────────────────────────────
# torchvision provides these via model weights metadata

# ─── Classification Model (ResNet18) ──────────────────────────

_classifier: Optional[torch.nn.Module] = None
_classifier_transforms = None
_classifier_labels: Optional[list[str]] = None


def _load_classifier():
    """Load ResNet18 pretrained on ImageNet (lazy, once)."""
    global _classifier, _classifier_transforms, _classifier_labels

    weights = models.ResNet18_Weights.IMAGENET1K_V1
    _classifier = models.resnet18(weights=weights)
    _classifier.eval()  # Inference mode: disables dropout, batchnorm uses running stats

    _classifier_transforms = weights.transforms()
    _classifier_labels = weights.meta["categories"]


def classify_image(image: Image.Image, top_k: int = 5) -> list[dict]:
    """
    Classify an image using pretrained ResNet18.

    Args:
        image: A PIL Image (any size, will be resized/normalized)
        top_k: Number of top predictions to return

    Returns:
        List of {label: str, confidence: float} sorted by confidence desc.
        Confidence values are softmax probabilities summing to ~1.0.
    """
    global _classifier, _classifier_transforms, _classifier_labels
    if _classifier is None:
        _load_classifier()

    # Preprocess: resize, center crop, normalize to ImageNet stats
    img_tensor = _classifier_transforms(image.convert("RGB")).unsqueeze(0)

    with torch.no_grad():
        output = _classifier(img_tensor)

    probabilities = torch.nn.functional.softmax(output[0], dim=0)
    top_probs, top_indices = torch.topk(probabilities, top_k)

    results = []
    for prob, idx in zip(top_probs, top_indices, strict=False):
        results.append({
            "label": _classifier_labels[idx.item()],
            "confidence": round(float(prob.item()), 4),
        })
    return results


# ─── Object Detection Model (Faster R-CNN) ────────────────────

_detector: Optional[torch.nn.Module] = None
_detector_labels: Optional[list[str]] = None

# COCO dataset class names (91 categories, index 0 is background)
COCO_LABELS = [
    "__background__", "person", "bicycle", "car", "motorcycle", "airplane",
    "bus", "train", "truck", "boat", "traffic light", "fire hydrant", "N/A",
    "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse",
    "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "N/A", "backpack",
    "umbrella", "N/A", "N/A", "handbag", "tie", "suitcase", "frisbee", "skis",
    "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "N/A", "wine glass",
    "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich",
    "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
    "chair", "couch", "potted plant", "bed", "N/A", "dining table", "N/A",
    "N/A", "toilet", "N/A", "tv", "laptop", "mouse", "remote", "keyboard",
    "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator",
    "N/A", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush",
]


def _load_detector():
    """Load Faster R-CNN pretrained on COCO (lazy, once)."""
    global _detector, _detector_labels

    weights = FasterRCNN_ResNet50_FPN_Weights.COCO_V1
    _detector = fasterrcnn_resnet50_fpn(weights=weights)
    _detector.eval()
    _detector_labels = COCO_LABELS


def detect_objects(
    image: Image.Image, confidence_threshold: float = 0.5, max_detections: int = 20
) -> list[dict]:
    """
    Detect objects in an image using pretrained Faster R-CNN.

    Args:
        image: A PIL Image (any size)
        confidence_threshold: Only return detections above this score
        max_detections: Cap on number of returned detections

    Returns:
        List of {label, confidence, bbox: [x1, y1, x2, y2]} dicts.
        Bbox coordinates are in pixels relative to the original image size.
    """
    global _detector, _detector_labels
    if _detector is None:
        _load_detector()

    # Convert to tensor [0, 1] range
    img_tensor = transforms.ToTensor()(image.convert("RGB")).unsqueeze(0)

    with torch.no_grad():
        predictions = _detector(img_tensor)[0]

    results = []
    for score, label_idx, box in zip(
        predictions["scores"], predictions["labels"], predictions["boxes"], strict=False
    ):
        if score.item() < confidence_threshold:
            continue
        if len(results) >= max_detections:
            break

        label = _detector_labels[label_idx.item()] if label_idx.item() < len(_detector_labels) else "unknown"
        if label in ("__background__", "N/A"):
            continue

        results.append({
            "label": label,
            "confidence": round(float(score.item()), 4),
            "bbox": [round(float(c), 1) for c in box.tolist()],
        })

    return results
