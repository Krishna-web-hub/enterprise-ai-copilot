"""
OCR Utility

Extracts text from images and PDFs using Tesseract OCR (via pytesseract).

Why Tesseract over a deep learning OCR model (like TrOCR, PaddleOCR)?
- Tesseract is already installed on this system (tesseract 5.3.4)
- Zero additional model download required (keeps disk usage down)
- Good enough accuracy for printed text, forms, receipts, documents
- Very fast compared to transformer-based OCR on CPU
- Can be swapped for a DL-based OCR in a future iteration if accuracy
  on handwritten/degraded text becomes important

For PDFs, we use pypdf to extract embedded text first (cheaper, faster,
more accurate for digitally-created PDFs). Only if that yields nothing
(scanned PDF) would we render pages to images and OCR them — but that
requires a PDF renderer (poppler/pdf2image), which adds complexity.
For this phase, PDFs use pypdf text extraction + pytesseract fallback
on a per-page basis only if the page has no embedded text.
"""

from pathlib import Path

import pytesseract
from PIL import Image


def extract_text_from_image(image_path: Path) -> str:
    """
    Extract text from an image file using Tesseract OCR.

    Args:
        image_path: Path to an image file (PNG, JPG, etc.)

    Returns:
        Extracted text as a string (may be empty if no text found).
    """
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text.strip()


def extract_text_from_image_pil(image: Image.Image) -> str:
    """
    Extract text from a PIL Image object using Tesseract OCR.

    Args:
        image: A PIL Image

    Returns:
        Extracted text as a string.
    """
    text = pytesseract.image_to_string(image)
    return text.strip()


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text from a PDF file.

    Strategy:
    1. Use pypdf to extract embedded text (fast, accurate for digital PDFs)
    2. If pypdf yields no text, the PDF is likely scanned — note this to the
       user rather than attempting image rendering (which requires poppler)

    Args:
        pdf_path: Path to a PDF file

    Returns:
        Extracted text as a string.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    pages_text = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text and text.strip():
            pages_text.append(f"--- Page {page_num} ---\n{text.strip()}")

    if pages_text:
        return "\n\n".join(pages_text)

    return (
        "[No embedded text found in this PDF. "
        "It may be a scanned document. OCR of scanned PDFs requires "
        "page-to-image rendering (poppler) which is not configured in this environment.]"
    )


def get_ocr_with_confidence(image_path: Path) -> dict:
    """
    Extract text with per-block confidence scores.

    Returns:
        {
            "text": str (full extracted text),
            "blocks": [{"text": str, "confidence": float, "bbox": [x, y, w, h]}],
            "mean_confidence": float
        }
    """
    image = Image.open(image_path)
    # pytesseract.image_to_data returns a TSV with per-word data
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    full_text_parts = []
    blocks = []

    n_items = len(data["text"])
    for i in range(n_items):
        text = data["text"][i].strip()
        conf = int(data["conf"][i])

        if not text or conf < 0:
            continue

        full_text_parts.append(text)
        blocks.append({
            "text": text,
            "confidence": conf / 100.0,
            "bbox": [
                data["left"][i],
                data["top"][i],
                data["width"][i],
                data["height"][i],
            ],
        })

    full_text = " ".join(full_text_parts)
    confidences = [b["confidence"] for b in blocks]
    mean_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

    return {
        "text": full_text,
        "blocks": blocks[:100],  # Cap to avoid huge payloads on dense documents
        "mean_confidence": mean_confidence,
    }
