/**
 * Vision / Deep Learning API Service
 *
 * Runs pretrained model inference on image and PDF datasets:
 * - Image classification (ResNet18, ImageNet)
 * - Object detection (Faster R-CNN, COCO)
 * - OCR text extraction (Tesseract)
 */

import api from './api';

// ─── Types ────────────────────────────────────────────────────

export interface ClassificationPrediction {
  label: string;
  confidence: number;
}

export interface DetectionItem {
  label: string;
  confidence: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
}

export interface VisionAnalysisResult {
  dataset_id: number;
  dataset_name: string;
  file_type: string;
  classification?: {
    model: string;
    predictions: ClassificationPrediction[];
  } | null;
  detection?: {
    model: string;
    detections: DetectionItem[];
    image_size: { width: number; height: number };
  } | null;
  ocr?: {
    method: string;
    text: string;
    char_count: number;
    mean_confidence?: number | null;
    word_count?: number | null;
  } | null;
}

// ─── API Function ─────────────────────────────────────────────

export async function analyzeDataset(
  datasetId: number,
  modes: string[] = ['all'],
  topK = 5,
  confidenceThreshold = 0.5
): Promise<VisionAnalysisResult> {
  const response = await api.post('/vision/analyze', {
    dataset_id: datasetId,
    modes,
    top_k: topK,
    confidence_threshold: confidenceThreshold,
  });
  return response.data;
}
