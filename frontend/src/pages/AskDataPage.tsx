/**
 * Ask Data Page — Query Terminal Aesthetic
 *
 * Natural-language-to-SQL interface styled as a robotic query terminal.
 * Features code-panel SQL display, cyber inputs, holographic results table.
 */

import { useEffect, useState } from 'react';
import {
  Database,
  Send,
  Code2,
  Table as TableIcon,
  Sparkles,
  AlertCircle,
  Clock,
  History,
  Terminal,
  Zap,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { Dataset, listDatasets } from '../services/datasets';
import { askQuestion, getQueryHistory, SQLQueryLogEntry, SQLQueryResult } from '../services/sql';

const STRUCTURED_TYPES = new Set(['csv', 'excel', 'json']);

const EXAMPLE_QUESTIONS = [
  'What are the top 5 rows by value?',
  'How many rows are there in total?',
  'Show me the average, minimum, and maximum values',
];

export default function AskDataPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null);
  const [isLoadingDatasets, setIsLoadingDatasets] = useState(true);
  const [question, setQuestion] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [result, setResult] = useState<SQLQueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<SQLQueryLogEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => { loadDatasets(); }, []);

  async function loadDatasets() {
    setIsLoadingDatasets(true);
    try {
      const response = await listDatasets(0, 100);
      const queryable = response.datasets.filter((d) => STRUCTURED_TYPES.has(d.file_type));
      setDatasets(queryable);
      if (queryable.length > 0 && queryable[0]) setSelectedDatasetId(queryable[0].id);
    } catch { /* empty */ }
    finally { setIsLoadingDatasets(false); }
  }

  async function loadHistory(datasetId: number) {
    try { const response = await getQueryHistory(datasetId, 0, 10); setHistory(response.logs); }
    catch { /* non-critical */ }
  }

  async function handleAsk() {
    if (!selectedDatasetId || !question.trim()) return;
    setIsAsking(true); setError(null); setResult(null);
    try {
      const data = await askQuestion(selectedDatasetId, question.trim());
      setResult(data);
      loadHistory(selectedDatasetId);
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setError(axiosErr.response?.data?.detail || 'Query processing failed');
      } else { setError('Query processing failed'); }
    } finally { setIsAsking(false); }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleAsk(); }
  }

  const selectedDataset = datasets.find((d) => d.id === selectedDatasetId);

  if (!isLoadingDatasets && datasets.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Query Engine</h1>
          <p className="mt-1 font-mono text-[10px] text-gray-500 uppercase tracking-wider">
            Natural language to SQL interface
          </p>
        </div>
        <div className="glass-panel p-12 text-center">
          <Database className="mx-auto h-10 w-10 text-gray-700" />
          <h3 className="mt-4 text-sm font-medium text-gray-400">No queryable datasets</h3>
          <p className="mt-1 font-mono text-[10px] text-gray-600">
            Upload a CSV, Excel, or JSON file to enable queries
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Query Engine</h1>
          <p className="mt-1 font-mono text-[10px] text-gray-500 uppercase tracking-wider">
            Natural language // SQL generation // Data analysis
          </p>
        </div>
        <button
          onClick={() => { setShowHistory((v) => !v); if (!showHistory && selectedDatasetId) loadHistory(selectedDatasetId); }}
          className="flex items-center gap-2 rounded-lg border border-robot-border/40 bg-robot-panel/50 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-gray-400 hover:text-neon-blue hover:border-cyber-400/40 transition-all"
        >
          <History className="h-3.5 w-3.5" />
          {showHistory ? 'Hide Log' : 'Query Log'}
        </button>
      </div>

      {/* Dataset selector */}
      <div className="glass-panel p-4">
        <div className="flex items-center gap-2 mb-2">
          <Database className="h-3.5 w-3.5 text-cyber-400/70" />
          <span className="hud-label">Target Dataset</span>
        </div>
        <select
          id="dataset-select"
          value={selectedDatasetId ?? ''}
          onChange={(e) => { const id = Number(e.target.value); setSelectedDatasetId(id); setResult(null); setError(null); if (showHistory) loadHistory(id); }}
          className="input-cyber"
        >
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>{d.name} ({d.row_count ?? '?'} rows, {d.column_count ?? '?'} cols)</option>
          ))}
        </select>
      </div>

      {/* Query input */}
      <div className="glass-panel p-4">
        <div className="flex items-center gap-2 mb-2">
          <Terminal className="h-3.5 w-3.5 text-cyber-400/70" />
          <span className="hud-label">Query Input</span>
        </div>
        <div className="flex gap-3">
          <textarea
            id="question-input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            placeholder="e.g. What are the top 5 products by price?"
            className="input-cyber flex-1 resize-none"
          />
          <motion.button
            onClick={handleAsk}
            disabled={isAsking || !question.trim() || !selectedDatasetId}
            className="flex items-center gap-2 self-start rounded-lg bg-cyber-600 px-4 py-3 font-mono text-xs uppercase tracking-wider text-white hover:bg-cyber-500 disabled:opacity-30 transition-all shadow-neon/50 hover:shadow-neon"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {isAsking ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" /> : <Send className="h-4 w-4" />}
            Execute
          </motion.button>
        </div>

        {/* Example prompts */}
        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLE_QUESTIONS.map((ex) => (
            <button
              key={ex}
              onClick={() => setQuestion(ex)}
              className="rounded-md border border-robot-border/30 bg-robot-darker/50 px-3 py-1 font-mono text-[10px] text-gray-500 hover:text-neon-blue hover:border-cyber-400/30 transition-all"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-mono text-xs text-red-400">
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Result */}
      {result && (
        <motion.div
          className="space-y-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {/* Explanation */}
          <div className="glass-panel p-5 border-l-2 border-l-neon-green/50">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="h-4 w-4 text-neon-green" />
              <span className="hud-label text-neon-green/70">Analysis Result</span>
            </div>
            <p className="text-sm leading-relaxed text-gray-200">{result.explanation}</p>
          </div>

          {/* Generated SQL */}
          <div className="glass-panel overflow-hidden">
            <div className="flex items-center justify-between border-b border-robot-border/30 px-5 py-3">
              <div className="flex items-center gap-2">
                <Code2 className="h-3.5 w-3.5 text-cyber-400/70" />
                <span className="hud-label">Generated SQL</span>
              </div>
              <span className="flex items-center gap-1 font-mono text-[9px] text-gray-600">
                <Clock className="h-3 w-3" />
                {result.execution_time_ms}ms
              </span>
            </div>
            <pre className="overflow-x-auto px-5 py-4 bg-robot-darker/50">
              <code className="font-mono text-xs text-neon-blue/90">{result.sql}</code>
            </pre>
          </div>

          {/* Results table */}
          <div className="glass-panel overflow-hidden">
            <div className="flex items-center justify-between border-b border-robot-border/30 px-5 py-3">
              <div className="flex items-center gap-2">
                <TableIcon className="h-3.5 w-3.5 text-neon-green/70" />
                <span className="hud-label">Query Results</span>
              </div>
              <span className="font-mono text-[9px] text-gray-600">{result.row_count} rows returned</span>
            </div>
            {result.rows.length === 0 ? (
              <div className="p-6 text-center font-mono text-xs text-gray-600">No rows returned</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-robot-border/20 bg-robot-darker/50">
                      {result.columns.map((col) => (
                        <th key={col} className="px-4 py-2.5 text-left font-mono text-[9px] uppercase tracking-wider text-gray-500">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, rowIdx) => (
                      <tr key={rowIdx} className="border-b border-robot-border/10 hover:bg-cyber-400/5 transition-colors">
                        {row.map((cell, colIdx) => (
                          <td key={colIdx} className="max-w-48 truncate px-4 py-2 font-mono text-[11px] text-gray-300">
                            {cell === null ? <span className="text-gray-700 italic">null</span> : String(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Query history */}
      {showHistory && (
        <div className="glass-panel overflow-hidden">
          <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
            <Zap className="h-3.5 w-3.5 text-cyber-400/70" />
            <span className="hud-label">Query Log {selectedDataset ? `// ${selectedDataset.name}` : ''}</span>
          </div>
          {history.length === 0 ? (
            <div className="p-6 text-center font-mono text-xs text-gray-600">No queries executed yet</div>
          ) : (
            <ul className="divide-y divide-robot-border/10">
              {history.map((entry) => (
                <li key={entry.id} className="px-5 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-xs text-gray-300">{entry.question}</p>
                    <span className={`flex-shrink-0 rounded-md border px-2 py-0.5 font-mono text-[9px] uppercase ${
                      entry.success ? 'border-neon-green/30 text-neon-green bg-neon-green/10' : 'border-red-500/30 text-red-400 bg-red-500/10'
                    }`}>
                      {entry.success ? `${entry.row_count} rows` : 'failed'}
                    </span>
                  </div>
                  {entry.generated_sql && (
                    <code className="mt-1 block truncate font-mono text-[10px] text-gray-600">{entry.generated_sql}</code>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
