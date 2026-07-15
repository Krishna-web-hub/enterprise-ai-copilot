/**
 * Shared TypeScript types for the frontend application.
 * These mirror the backend Pydantic schemas.
 */

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

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

export interface ChatSession {
  id: number;
  title: string;
  created_at: string;
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface MLModel {
  id: number;
  name: string;
  model_type: string;
  algorithm: string;
  metrics: Record<string, number>;
  feature_importance: Record<string, number> | null;
  created_at: string;
}

export interface Report {
  id: number;
  title: string;
  report_type: string;
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}
