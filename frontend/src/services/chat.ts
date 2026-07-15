/**
 * Chat API Service
 *
 * Handles chat sessions and agentic AI messaging:
 * - Create/list/rename/delete chat sessions
 * - Pin/unpin sessions (max 5 pinned)
 * - Send messages (triggers the agentic pipeline)
 * - Retrieve conversation history
 */

import api from './api';

// ─── Types ────────────────────────────────────────────────────

export interface ChatSession {
  id: number;
  title: string;
  is_pinned: boolean;
  pin_order: number;
  created_at: string;
}

export interface ChatSessionListResponse {
  sessions: ChatSession[];
  total: number;
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  metadata: AgentMetadata | null;
  created_at: string;
}

export interface AgentMetadata {
  plan_reasoning?: string;
  plan_steps?: { agent: string; instruction: string }[];
  agents_used?: string[];
  step_results?: { agent: string; success: boolean; result?: string }[];
  total_time_ms?: number;
}

export interface ChatMessagesResponse {
  messages: ChatMessage[];
  total: number;
}

// ─── Session API Functions ────────────────────────────────────

export async function createSession(title = 'New Chat'): Promise<ChatSession> {
  const response = await api.post('/chat/sessions', { title });
  return response.data;
}

export async function listSessions(): Promise<ChatSessionListResponse> {
  const response = await api.get('/chat/sessions');
  return response.data;
}

export async function renameSession(sessionId: number, title: string): Promise<ChatSession> {
  const response = await api.patch(`/chat/sessions/${sessionId}`, { title });
  return response.data;
}

export async function deleteSession(sessionId: number): Promise<void> {
  await api.delete(`/chat/sessions/${sessionId}`);
}

export async function pinSession(sessionId: number): Promise<ChatSession> {
  const response = await api.post(`/chat/sessions/${sessionId}/pin`);
  return response.data;
}

export async function unpinSession(sessionId: number): Promise<ChatSession> {
  const response = await api.delete(`/chat/sessions/${sessionId}/pin`);
  return response.data;
}

// ─── Message API Functions ────────────────────────────────────

export async function sendMessage(sessionId: number, content: string): Promise<ChatMessage> {
  const response = await api.post(`/chat/sessions/${sessionId}/messages`, { content });
  return response.data;
}

export async function sendMultimodalMessage(
  sessionId: number,
  content: string,
  files: File[]
): Promise<ChatMessage> {
  const formData = new FormData();
  formData.append('content', content);
  for (const file of files) {
    formData.append('files', file);
  }
  const response = await api.post(
    `/chat/sessions/${sessionId}/messages/multimodal`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return response.data;
}

export async function getMessages(sessionId: number): Promise<ChatMessagesResponse> {
  const response = await api.get(`/chat/sessions/${sessionId}/messages`);
  return response.data;
}
