/**
 * Documents Page — Vault/Archive Aesthetic
 *
 * Document Q&A with RAG, styled as a cyber vault. Status badges as
 * neon indicators, query interface as terminal prompt.
 */

import { useEffect, useState } from 'react';
import {
  Upload,
  FileText,
  Send,
  Trash2,
  AlertCircle,
  CheckCircle,
  X,
  BookOpen,
  Loader2,
  Shield,
  Search,
} from 'lucide-react';
import { motion } from 'framer-motion';
import {
  RAGDocument,
  RAGQueryResponse,
  RAGSource,
  deleteRAGDocument,
  ingestDocument,
  listRAGDocuments,
  queryDocuments,
} from '../services/rag';

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: 'border-neon-green/40 text-neon-green bg-neon-green/10',
    processing: 'border-yellow-400/40 text-yellow-400 bg-yellow-400/10',
    pending: 'border-gray-500/40 text-gray-400 bg-gray-500/10',
    failed: 'border-red-500/40 text-red-400 bg-red-500/10',
  };
  return (
    <span className={`rounded-md border px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider ${styles[status] || styles.pending}`}>
      {status}
    </span>
  );
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<RAGDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [question, setQuestion] = useState('');
  const [isQuerying, setIsQuerying] = useState(false);
  const [queryResult, setQueryResult] = useState<RAGQueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);

  useEffect(() => { loadDocuments(); }, []);

  async function loadDocuments() {
    setIsLoading(true);
    try { const response = await listRAGDocuments(); setDocuments(response.documents); }
    catch { /* empty */ }
    finally { setIsLoading(false); }
  }

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploadError(null); setUploadSuccess(null); setIsUploading(true);
    try {
      for (let i = 0; i < files.length; i++) { const file = files[i]; if (file) await ingestDocument(file); }
      const firstName = files[0]?.name ?? 'file';
      setUploadSuccess(files.length === 1 ? `"${firstName}" ingested for RAG` : `${files.length} documents processed`);
      await loadDocuments();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setUploadError(axiosErr.response?.data?.detail || 'Upload failed');
      } else { setUploadError('Upload failed'); }
    } finally { setIsUploading(false); }
  }

  async function handleDelete(docId: number) {
    if (!confirm('Remove from vault? Content will no longer be searchable.')) return;
    try { await deleteRAGDocument(docId); await loadDocuments(); }
    catch { setUploadError('Failed to delete document'); }
  }

  async function handleQuery() {
    if (!question.trim()) return;
    setIsQuerying(true); setQueryError(null); setQueryResult(null);
    try { const result = await queryDocuments(question.trim()); setQueryResult(result); }
    catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setQueryError(axiosErr.response?.data?.detail || 'Query failed');
      } else { setQueryError('Query failed'); }
    } finally { setIsQuerying(false); }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleQuery(); }
  }

  const completedDocs = documents.filter((d) => d.embedding_status === 'completed');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Document Vault</h1>
        <p className="mt-1 font-mono text-[10px] text-gray-500 uppercase tracking-wider">
          RAG knowledge base // Upload, index, and query documents
        </p>
      </div>

      {/* Notifications */}
      {uploadError && (
        <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-mono text-xs text-red-400">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span className="flex-1">{uploadError}</span>
          <button onClick={() => setUploadError(null)}><X className="h-3.5 w-3.5" /></button>
        </div>
      )}
      {uploadSuccess && (
        <div className="flex items-center gap-3 rounded-lg border border-neon-green/30 bg-neon-green/10 px-4 py-3 font-mono text-xs text-neon-green">
          <CheckCircle className="h-4 w-4 flex-shrink-0" />
          <span className="flex-1">{uploadSuccess}</span>
          <button onClick={() => setUploadSuccess(null)}><X className="h-3.5 w-3.5" /></button>
        </div>
      )}

      {/* Upload section */}
      <div className="glass-panel p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-3.5 w-3.5 text-cyber-400/70" />
            <span className="hud-label">Ingest Documents</span>
          </div>
          <label className="btn-cyber-filled cursor-pointer text-xs">
            <Upload className="h-3.5 w-3.5 mr-2 inline" />
            {isUploading ? 'Processing...' : 'Upload'}
            <input type="file" className="hidden" multiple accept=".pdf,.docx,.doc,.txt" onChange={(e) => handleUpload(e.target.files)} disabled={isUploading} />
          </label>
        </div>
        <p className="mt-2 font-mono text-[9px] text-gray-600 uppercase tracking-wider">Supported: PDF, Word (.docx), Plain Text (.txt)</p>
      </div>

      {/* Document list */}
      {!isLoading && documents.length > 0 && (
        <div className="glass-panel overflow-hidden">
          <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
            <BookOpen className="h-3.5 w-3.5 text-cyber-400/70" />
            <span className="hud-label">Vault Index</span>
            <span className="ml-auto font-mono text-[9px] text-gray-600">{completedDocs.length}/{documents.length} ready</span>
          </div>
          <ul className="divide-y divide-robot-border/10">
            {documents.map((doc, idx) => (
              <motion.li
                key={doc.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.03 }}
                className="flex items-center gap-4 px-5 py-3 hover:bg-cyber-400/5 transition-colors"
              >
                <span className="font-mono text-[9px] text-gray-700 w-4">{String(idx + 1).padStart(2, '0')}</span>
                <div className="flex h-7 w-7 items-center justify-center rounded-md bg-robot-darker border border-robot-border/30">
                  <FileText className="h-3.5 w-3.5 text-blue-400" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-gray-200">{doc.name}</p>
                  <p className="font-mono text-[9px] text-gray-600">{doc.file_type.toUpperCase()} // {doc.chunk_count} chunks</p>
                </div>
                <StatusBadge status={doc.embedding_status} />
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="rounded-md p-1.5 text-gray-600 hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/30 transition-all"
                  aria-label="Delete"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </motion.li>
            ))}
          </ul>
        </div>
      )}

      {!isLoading && documents.length === 0 && (
        <div className="glass-panel p-12 text-center">
          <BookOpen className="mx-auto h-10 w-10 text-gray-700" />
          <h3 className="mt-4 text-sm font-medium text-gray-400">Vault empty</h3>
          <p className="mt-1 font-mono text-[10px] text-gray-600">Upload documents to enable AI-powered Q&A</p>
        </div>
      )}

      {/* Query section */}
      {completedDocs.length > 0 && (
        <div className="glass-panel p-5">
          <div className="flex items-center gap-2 mb-3">
            <Search className="h-3.5 w-3.5 text-cyber-400/70" />
            <span className="hud-label">Knowledge Query</span>
          </div>
          <div className="flex gap-3">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder="e.g. What is the company's leave policy?"
              className="input-cyber flex-1 resize-none"
            />
            <motion.button
              onClick={handleQuery}
              disabled={isQuerying || !question.trim()}
              className="flex items-center gap-2 self-start rounded-lg bg-cyber-600 px-4 py-3 font-mono text-xs uppercase text-white hover:bg-cyber-500 disabled:opacity-30 transition-all"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {isQuerying ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Query
            </motion.button>
          </div>

          {queryError && (
            <div className="mt-3 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-mono text-xs text-red-400">
              <AlertCircle className="h-4 w-4" />{queryError}
            </div>
          )}

          {queryResult && (
            <motion.div className="mt-4 space-y-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <div className="rounded-lg border border-neon-green/20 bg-neon-green/5 p-4">
                <p className="text-sm leading-relaxed text-gray-200 whitespace-pre-wrap">{queryResult.answer}</p>
              </div>

              {queryResult.sources.length > 0 && (
                <div>
                  <span className="hud-label">Sources</span>
                  <div className="mt-2 space-y-2">
                    {queryResult.sources.map((source: RAGSource) => (
                      <div key={source.source_number} className="rounded-lg border border-robot-border/30 bg-robot-darker/50 p-3">
                        <div className="flex items-center gap-2 font-mono text-[10px]">
                          <span className="flex h-5 w-5 items-center justify-center rounded-md bg-cyber-400/10 border border-cyber-400/30 text-neon-blue text-[9px]">
                            {source.source_number}
                          </span>
                          <span className="text-gray-300">{source.document_name}</span>
                          {source.page_number && <span className="text-gray-600">p.{source.page_number}</span>}
                          <span className="ml-auto text-gray-600">{(source.score * 100).toFixed(0)}% match</span>
                        </div>
                        <p className="mt-1 font-mono text-[10px] text-gray-500 line-clamp-2">{source.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
}
