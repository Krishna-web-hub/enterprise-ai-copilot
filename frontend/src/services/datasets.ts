/**
 * Dataset API Service
 *
 * Handles all dataset-related API calls:
 * - Upload files
 * - List datasets
 * - Get dataset details
 * - Preview dataset rows
 * - Delete datasets
 *
 * Uses the shared Axios instance (with auth token injection).
 */

import api from './api';

// ─── Types ────────────────────────────────────────────────────

export interface ColumnMetadata {
  name: string;
  dtype: string;
  null_count: number;
  null_percent: number;
  unique_count: number;
  sample_values: string[];
}

export interface Dataset {
  id: number;
  name: string;
  file_type: string;
  file_size_bytes: number;
  row_count: number | null;
  column_count: number | null;
  columns_metadata: ColumnMetadata[] | null;
  description: string | null;
  created_at: string;
}

export interface DatasetListResponse {
  datasets: Dataset[];
  total: number;
  skip: number;
  limit: number;
}

export interface DatasetPreview {
  columns: string[];
  rows: (string | number | boolean | null)[][];
  total_rows: number;
  preview_rows: number;
  dtypes: Record<string, string>;
  message?: string;
}

// ─── API Functions ────────────────────────────────────────────

/**
 * Upload a file to create a new dataset.
 * Uses multipart/form-data for file transfer.
 */
export async function uploadDataset(file: File): Promise<Dataset> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/data/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
}

/**
 * List user's datasets with pagination.
 */
export async function listDatasets(
  skip = 0,
  limit = 20
): Promise<DatasetListResponse> {
  const response = await api.get('/data/datasets', {
    params: { skip, limit },
  });
  return response.data;
}

/**
 * Get a single dataset's details.
 */
export async function getDataset(datasetId: number): Promise<Dataset> {
  const response = await api.get(`/data/datasets/${datasetId}`);
  return response.data;
}

/**
 * Get preview data (first N rows) of a structured dataset.
 */
export async function getDatasetPreview(
  datasetId: number,
  rows = 50
): Promise<DatasetPreview> {
  const response = await api.get(`/data/datasets/${datasetId}/preview`, {
    params: { rows },
  });
  return response.data;
}

/**
 * Delete a dataset and its file.
 */
export async function deleteDataset(datasetId: number): Promise<void> {
  await api.delete(`/data/datasets/${datasetId}`);
}


// ─── Analytics Types ──────────────────────────────────────────

export interface AnalyticsSummary {
  row_count: number;
  column_count: number;
  total_cells: number;
  total_nulls: number;
  data_quality_percent: number;
  memory_mb: number;
  duplicate_rows: number;
}

export interface NumericStats {
  mean: number;
  median: number | null;
  std: number;
  min: number;
  max: number;
  q25: number;
  q75: number;
  skewness: number;
  kurtosis: number;
}

export interface Distribution {
  bins: number[];
  counts: number[];
}

export interface TopValue {
  value: string;
  count: number;
  percent: number;
}

export interface ColumnAnalytics {
  name: string;
  dtype: string;
  type: 'numeric' | 'categorical' | 'datetime' | 'other';
  null_count: number;
  null_percent: number;
  unique_count: number;
  unique_percent: number;
  stats?: NumericStats | { min: string; max: string; range_days: number };
  distribution?: Distribution;
  top_values?: TopValue[];
}

export interface CorrelationData {
  columns: string[];
  matrix: number[][];
}

export interface NullAnalysisItem {
  column: string;
  null_count: number;
  null_percent: number;
}

export interface DatasetAnalytics {
  dataset_id: number;
  dataset_name: string;
  summary: AnalyticsSummary;
  data_types: { numeric: number; categorical: number; datetime: number; other: number };
  columns: ColumnAnalytics[];
  correlations: CorrelationData | null;
  null_analysis: NullAnalysisItem[];
}

// ─── Analytics API Function ───────────────────────────────────

export async function getDatasetAnalytics(datasetId: number): Promise<DatasetAnalytics> {
  const response = await api.get(`/data/datasets/${datasetId}/analytics`);
  return response.data;
}
