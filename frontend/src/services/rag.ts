/**
 * RAG (Document Q&A) API Service
 *
 * Handles document ingestion and retrieval-augmented question answering:
 * - Upload documents for RAG processing
 * - Ask questions with cited answers
 * - List/delete ingested documents
 */

import api from './api';

// ─── Types ────────────────────────────────────────────────────

export interface RAGDocument {
  id: number;
  name: string;
  file_type: string;
  chunk_count: number;
  embedding_status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
}

export interface RAGDocumentListResponse {
  documents: RAGDocument[];
  total: number;
}

export interface RAGSource {
  source_number: number;
  document_name: string;
  page_number: number | null;
  text: string;
  score: number;
}

export interface RAGQueryResponse {
  answer: string;
  sources: RAGSource[];
}

// ─── API Functions ────────────────────────────────────────────

/**
 * Upload and ingest a document for RAG (chunk, embed, store).
 */
export async function ingestDocument(file: File): Promise<RAGDocument> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/rag/ingest', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

/**
 * Ask a question about ingested documents.
 */
export async function queryDocuments(question: string, topK = 5): Promise<RAGQueryResponse> {
  const response = await api.post('/rag/query', { question, top_k: topK });
  return response.data;
}

/**
 * List all RAG-ingested documents with their status.
 */
export async function listRAGDocuments(): Promise<RAGDocumentListResponse> {
  const response = await api.get('/rag/documents');
  return response.data;
}

/**
 * Delete a document from RAG (removes vectors + file).
 */
export async function deleteRAGDocument(documentId: number): Promise<void> {
  await api.delete(`/rag/documents/${documentId}`);
}
