/**
 * ML Engine API Service
 *
 * Handles model training, prediction, and model management:
 * - Train a model (classification/regression/clustering/anomaly_detection)
 * - List/get/delete trained models
 * - Run predictions against a trained model
 */

import api from './api';

// ─── Types ────────────────────────────────────────────────────

export type ModelType = 'classification' | 'regression' | 'clustering' | 'anomaly_detection';

export interface TrainRequest {
  dataset_id: number;
  model_type: ModelType;
  target_column?: string | null;
  algorithm?: string | null;
  feature_columns?: string[] | null;
  name?: string | null;
}

export interface TrainedModel {
  id: number;
  name: string;
  model_type: ModelType;
  algorithm: string;
  metrics: Record<string, number>;
  feature_importance: Record<string, number> | null;
  training_duration_seconds: number | null;
  created_at: string;
}

export interface ModelSummary {
  id: number;
  name: string;
  model_type: ModelType;
  algorithm: string;
  metrics: Record<string, number>;
  created_at: string;
}

export interface ModelListResponse {
  models: ModelSummary[];
  total: number;
}

export interface ModelDetail {
  id: number;
  name: string;
  model_type: ModelType;
  algorithm: string;
  target_column: string | null;
  feature_columns: string[];
  metrics: Record<string, number>;
  feature_importance: Record<string, number> | null;
  parameters: Record<string, unknown> | null;
  training_duration_seconds: number | null;
  created_at: string;
}

export interface PredictionResult {
  prediction: string | number;
  confidence: number | null;
  explanation: string;
}

export interface PredictResponse {
  predictions: PredictionResult[];
  model_id: number;
  model_name: string;
}

// ─── API Functions ────────────────────────────────────────────

export async function trainModel(request: TrainRequest): Promise<TrainedModel> {
  const response = await api.post('/ml/train', request, { timeout: 150000 }); // 2.5 min timeout
  return response.data;
}

export async function listModels(skip = 0, limit = 20): Promise<ModelListResponse> {
  const response = await api.get('/ml/models', { params: { skip, limit } });
  return response.data;
}

export async function getModel(modelId: number): Promise<ModelDetail> {
  const response = await api.get(`/ml/models/${modelId}`);
  return response.data;
}

export async function deleteModel(modelId: number): Promise<void> {
  await api.delete(`/ml/models/${modelId}`);
}

export async function predict(
  modelId: number,
  inputData: Record<string, unknown> | Record<string, unknown>[]
): Promise<PredictResponse> {
  const response = await api.post('/ml/predict', {
    model_id: modelId,
    input_data: inputData,
  });
  return response.data;
}

export async function getSampleInput(modelId: number): Promise<Record<string, string>> {
  const response = await api.get(`/ml/models/${modelId}/sample-input`);
  return response.data.sample;
}
