/**
 * Reports API Service
 *
 * Handles AI-powered report generation and retrieval.
 */

import api from './api';

export type ReportType =
  | 'executive_summary'
  | 'sales_analysis'
  | 'customer_insights'
  | 'anomaly_report'
  | 'forecast_report'
  | 'recommendation_report';

export interface GenerateReportRequest {
  report_type: ReportType;
  dataset_id?: number | null;
  additional_context?: string | null;
}

export interface Report {
  id: number;
  title: string;
  report_type: string;
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ReportListResponse {
  reports: Report[];
  total: number;
}

export async function generateReport(request: GenerateReportRequest): Promise<Report> {
  const response = await api.post('/reports/generate', request);
  return response.data;
}

export async function listReports(): Promise<ReportListResponse> {
  const response = await api.get('/reports/reports');
  return response.data;
}

export async function getReport(reportId: number): Promise<Report> {
  const response = await api.get(`/reports/reports/${reportId}`);
  return response.data;
}

export async function deleteReport(reportId: number): Promise<void> {
  await api.delete(`/reports/reports/${reportId}`);
}
