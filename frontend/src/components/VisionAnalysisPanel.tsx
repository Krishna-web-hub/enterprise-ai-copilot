/**
 * Vision Analysis Panel
 *
 * Displays AI-powered analysis results for image and PDF datasets.
 * Shows an "Analyze" button, then renders classification labels,
 * detected objects, and/or extracted OCR text once results arrive.
 *
 * Integrated into the Datasets detail view for image/PDF file types.
 */

import { useState } from 'react';
import { Eye, Sparkles, AlertCircle, Tag, ScanSearch, FileText } from 'lucide-react';
import { analyzeDataset, VisionAnalysisResult } from '../services/vision';

interface Props {
  datasetId: number;
  fileType: string;
}

const VISION_TYPES = new Set(['image', 'pdf']);

export default function VisionAnalysisPanel({ datasetId, fileType }: Props) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<VisionAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!VISION_TYPES.has(fileType)) return null;

  async function handleAnalyze() {
    setIsAnalyzing(true);
    setError(null);
    setResult(null);

    try {
      const data = await analyzeDataset(datasetId, ['all']);
      setResult(data);
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setError(axiosErr.response?.data?.detail || 'Analysis failed');
      } else {
        setError('Analysis failed');
      }
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <div className="rounded-xl bg-white dark:bg-gray-800 shadow-sm">
      <div className="flex items-center justify-between border-b dark:border-gray-700 px-6 py-4">
        <div className="flex items-center gap-2">
          <Eye className="h-5 w-5 text-purple-600" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">AI Vision Analysis</h2>
        </div>
        {!result && (
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing}
            className="flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
          >
            {isAnalyzing ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Analyze with AI
              </>
            )}
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 px-6 py-4 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6 p-6">
          {/* Classification */}
          {result.classification && (
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                <Tag className="h-4 w-4" />
                Image Classification
                <span className="ml-auto text-xs font-normal text-gray-400">
                  {result.classification.model}
                </span>
              </div>
              <div className="mt-3 space-y-2">
                {result.classification.predictions.map((pred, idx) => (
                  <div key={idx} className="flex items-center gap-3">
                    <span className="w-32 truncate text-sm text-gray-700 dark:text-gray-300">{pred.label}</span>
                    <div className="h-2 flex-1 rounded-full bg-gray-100">
                      <div
                        className="h-2 rounded-full bg-purple-500"
                        style={{ width: `${pred.confidence * 100}%` }}
                      />
                    </div>
                    <span className="w-14 text-right text-xs text-gray-500 dark:text-gray-400">
                      {(pred.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Detection */}
          {result.detection && result.detection.detections.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                <ScanSearch className="h-4 w-4" />
                Object Detection
                <span className="ml-auto text-xs font-normal text-gray-400">
                  {result.detection.model}
                </span>
              </div>
              <div className="mt-3">
                <div className="flex flex-wrap gap-2">
                  {result.detection.detections.map((det, idx) => (
                    <span
                      key={idx}
                      className="rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700"
                    >
                      {det.label}{' '}
                      <span className="text-blue-400">
                        ({(det.confidence * 100).toFixed(0)}%)
                      </span>
                    </span>
                  ))}
                </div>
                <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                  {result.detection.detections.length} object(s) detected in{' '}
                  {result.detection.image_size.width}×{result.detection.image_size.height} image
                </p>
              </div>
            </div>
          )}

          {result.detection && result.detection.detections.length === 0 && (
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <ScanSearch className="h-4 w-4" />
              No objects detected above confidence threshold.
            </div>
          )}

          {/* OCR */}
          {result.ocr && (
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                <FileText className="h-4 w-4" />
                Text Extraction (OCR)
                <span className="ml-auto text-xs font-normal text-gray-400">
                  {result.ocr.method}
                  {result.ocr.mean_confidence != null && (
                    <> &middot; confidence: {(result.ocr.mean_confidence * 100).toFixed(0)}%</>
                  )}
                </span>
              </div>
              {result.ocr.text ? (
                <pre className="mt-3 max-h-64 overflow-y-auto rounded-lg bg-gray-50 dark:bg-gray-800/50 p-4 text-xs text-gray-700 whitespace-pre-wrap">
                  {result.ocr.text}
                </pre>
              ) : (
                <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">No text found in this file.</p>
              )}
              <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                {result.ocr.char_count} characters
                {result.ocr.word_count != null && <> &middot; {result.ocr.word_count} words</>}
              </p>
            </div>
          )}

          {/* Re-analyze button */}
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing}
            className="text-sm text-purple-600 hover:text-purple-700 disabled:opacity-50"
          >
            {isAnalyzing ? 'Analyzing...' : 'Re-analyze'}
          </button>
        </div>
      )}

      {/* Prompt before analysis */}
      {!result && !error && !isAnalyzing && (
        <div className="px-6 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
          Click "Analyze with AI" to run image classification, object detection, and text extraction.
          {fileType === 'pdf' && ' (For PDFs, only text extraction is available.)'}
        </div>
      )}
    </div>
  );
}
