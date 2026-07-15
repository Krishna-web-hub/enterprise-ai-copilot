/**
 * SQL Engine API Service
 *
 * Handles natural-language-to-SQL queries against a dataset:
 * - Ask a question, get back generated SQL, results, and an explanation
 * - Fetch query history for the "recent queries" panel
 */

import api from './api';

// ─── Types ────────────────────────────────────────────────────

export interface SQLQueryResult {
  sql: string;
  columns: string[];
  rows: (string | number | boolean | null)[][];
  row_count: number;
  explanation: string;
  execution_time_ms: number;
}

export interface SQLQueryLogEntry {
  id: number;
  dataset_id: number;
  question: string;
  generated_sql: string | null;
  row_count: number | null;
  execution_time_ms: number | null;
  success: boolean;
  error_message: string | null;
  created_at: string;
}

export interface SQLQueryLogListResponse {
  logs: SQLQueryLogEntry[];
  total: number;
}

// ─── API Functions ────────────────────────────────────────────

/**
 * Ask a natural-language question about a dataset.
 * The backend generates SQL, executes it, and returns an explanation.
 */
export async function askQuestion(
  datasetId: number,
  question: string
): Promise<SQLQueryResult> {
  const response = await api.post('/sql/query', {
    dataset_id: datasetId,
    question,
  });
  return response.data;
}

/**
 * Get past queries, optionally filtered by dataset.
 */
export async function getQueryHistory(
  datasetId?: number,
  skip = 0,
  limit = 20
): Promise<SQLQueryLogListResponse> {
  const response = await api.get('/sql/history', {
    params: { dataset_id: datasetId, skip, limit },
  });
  return response.data;
}
