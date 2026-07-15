/**
 * Dashboard API Service
 *
 * Fetches dashboard summary data (counts, recent activity).
 */

import api from './api';

export interface DashboardData {
  total_datasets: number;
  total_models: number;
  total_reports: number;
  total_documents: number;
  total_chat_sessions: number;
  recent_chats: { id: number; title: string; created_at: string }[];
  recent_datasets: { id: number; name: string; file_type: string; created_at: string }[];
}

export async function getDashboard(): Promise<DashboardData> {
  const response = await api.get('/reports/dashboard');
  return response.data;
}
