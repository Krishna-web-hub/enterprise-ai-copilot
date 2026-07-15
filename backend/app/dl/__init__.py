"""
Deep Learning Module

Provides pretrained vision model inference (not training):
- Image classification (ResNet18, ImageNet classes)
- Object detection (Faster R-CNN, COCO classes)
- OCR (pytesseract wrapper)

These models are loaded lazily (first call triggers download/load) and
cached as module-level singletons to avoid reloading 100+ MB of weights
on every request.
"""
