/**
 * Reports Page — Holographic Frame Aesthetic
 *
 * AI-powered report generation with data-panel cards,
 * command-input generation form, and cyber detail view.
 */

import { useEffect, useState } from 'react';
import {
  FileText,
  Plus,
  ChevronLeft,
  Trash2,
  Loader2,
  AlertCircle,
  CheckCircle,
  X,
  Zap,
  BookOpen,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { Dataset, listDatasets } from '../services/datasets';
import {
  Report,
  ReportType,
  deleteReport,
  generateReport,
  getReport,
  listReports,
} from '../services/reports';

const REPORT_TYPE_OPTIONS: { value: ReportType; label: string; description: string }[] = [
  { value: 'executive_summary', label: 'Executive Summary', description: 'High-level overview' },
  { value: 'sales_analysis', label: 'Sales Analysis', description: 'Revenue trends' },
  { value: 'customer_insights', label: 'Customer Insights', description: 'Segmentation patterns' },
  { value: 'anomaly_report', label: 'Anomaly Report', description: 'Risk indicators' },
  { value: 'forecast_report', label: 'Forecast Report', description: 'Projected trends' },
  { value: 'recommendation_report', label: 'Recommendations', description: 'Action items' },
];

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [reportType, setReportType] = useState<ReportType>('executive_summary');
  const [datasetId, setDatasetId] = useState<number | ''>('');
  const [additionalContext, setAdditionalContext] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => { loadReports(); }, []);

  async function loadReports() {
    setIsLoading(true);
    try { const response = await listReports(); setReports(response.reports); }
    catch { /* empty */ }
    finally { setIsLoading(false); }
  }

  async function loadDatasetsForForm() {
    try { const response = await listDatasets(0, 100); setDatasets(response.datasets.filter(d => ['csv', 'excel', 'json'].includes(d.file_type))); }
    catch { /* none available */ }
  }

  function openForm() { setShowForm(true); setError(null); setSuccess(null); loadDatasetsForForm(); }

  async function handleGenerate() {
    setIsGenerating(true); setError(null);
    try {
      const report = await generateReport({ report_type: reportType, dataset_id: datasetId ? Number(datasetId) : null, additional_context: additionalContext || null });
      setSuccess(`"${report.title}" generated`);
      setShowForm(false); setAdditionalContext('');
      await loadReports();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setError(axiosErr.response?.data?.detail || 'Generation failed');
      } else { setError('Generation failed'); }
    } finally { setIsGenerating(false); }
  }

  async function handleSelect(reportId: number) {
    try { const report = await getReport(reportId); setSelectedReport(report); }
    catch { /* stay on list */ }
  }

  async function handleDelete(reportId: number) {
    if (!confirm('Delete this report?')) return;
    try { await deleteReport(reportId); setSelectedReport(null); await loadReports(); }
    catch { /* non-critical */ }
  }

  // ─── Detail View ────────────────────────────────────────────
  if (selectedReport) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <motion.button onClick={() => setSelectedReport(null)} className="rounded-lg p-2 text-gray-500 hover:text-neon-blue hover:bg-cyber-400/10 border border-transparent hover:border-cyber-400/30 transition-all" whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
            <ChevronLeft className="h-5 w-5" />
          </motion.button>
          <div className="flex-1">
            <h1 className="text-xl font-bold text-white">{selectedReport.title}</h1>
            <p className="mt-0.5 font-mono text-[10px] text-gray-500 uppercase tracking-wider">Generated {formatDate(selectedReport.created_at)}</p>
          </div>
          <button onClick={() => handleDelete(selectedReport.id)} className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs font-mono uppercase text-red-400 hover:bg-red-500/20 transition-all">
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </button>
        </div>

        <div className="glass-panel p-8">
          <div className="prose prose-sm prose-invert max-w-none text-gray-300 whitespace-pre-wrap leading-relaxed font-sans">
            {selectedReport.content}
          </div>
        </div>
      </div>
    );
  }

  // ─── List View ──────────────────────────────────────────────
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Report Generator</h1>
          <p className="mt-1 font-mono text-[10px] text-gray-500 uppercase tracking-wider">
            AI-powered business intelligence reports
          </p>
        </div>
        <motion.button onClick={openForm} className="btn-cyber-filled" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
          <Plus className="h-4 w-4 mr-2 inline" /> Generate
        </motion.button>
      </div>

      {success && (
        <div className="flex items-center gap-3 rounded-lg border border-neon-green/30 bg-neon-green/10 px-4 py-3 font-mono text-xs text-neon-green">
          <CheckCircle className="h-4 w-4" /><span className="flex-1">{success}</span>
          <button onClick={() => setSuccess(null)}><X className="h-3.5 w-3.5" /></button>
        </div>
      )}

      {/* Generate form */}
      {showForm && (
        <div className="glass-panel p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-neon-blue" />
              <span className="text-sm font-medium text-white">Generate Report</span>
            </div>
            <button onClick={() => setShowForm(false)}><X className="h-4 w-4 text-gray-500 hover:text-white transition-colors" /></button>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="hud-label mb-1 block">Report Type</label>
              <select value={reportType} onChange={(e) => setReportType(e.target.value as ReportType)} className="input-cyber">
                {REPORT_TYPE_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label} — {opt.description}</option>)}
              </select>
            </div>
            <div>
              <label className="hud-label mb-1 block">Dataset (optional)</label>
              <select value={datasetId} onChange={(e) => setDatasetId(e.target.value ? Number(e.target.value) : '')} className="input-cyber">
                <option value="">No dataset (general)</option>
                {datasets.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="hud-label mb-1 block">Additional Instructions</label>
              <textarea value={additionalContext} onChange={(e) => setAdditionalContext(e.target.value)} rows={2} placeholder="e.g. Focus on Q3 performance..." className="input-cyber resize-none" />
            </div>
            {error && (
              <div className="sm:col-span-2 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-mono text-xs text-red-400">
                <AlertCircle className="h-4 w-4" />{error}
              </div>
            )}
            <div className="sm:col-span-2">
              <motion.button onClick={handleGenerate} disabled={isGenerating} className="btn-cyber-filled" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                {isGenerating ? <><Loader2 className="h-4 w-4 animate-spin mr-2 inline" />Generating...</> : 'Execute Generation'}
              </motion.button>
            </div>
          </div>
        </div>
      )}

      {/* Report list */}
      {isLoading ? (
        <div className="flex justify-center py-12"><div className="h-6 w-6 animate-spin rounded-full border-2 border-neon-blue border-t-transparent" /></div>
      ) : reports.length === 0 ? (
        <div className="glass-panel p-12 text-center">
          <FileText className="mx-auto h-10 w-10 text-gray-700" />
          <h3 className="mt-4 text-sm font-medium text-gray-400">No reports generated</h3>
          <p className="mt-1 font-mono text-[10px] text-gray-600">Generate an executive summary, analysis, or forecast</p>
        </div>
      ) : (
        <div className="glass-panel overflow-hidden">
          <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
            <BookOpen className="h-3.5 w-3.5 text-cyber-400/70" />
            <span className="hud-label">Report Archive</span>
            <span className="ml-auto font-mono text-[9px] text-gray-600">{reports.length} reports</span>
          </div>
          <ul className="divide-y divide-robot-border/10">
            {reports.map((report, idx) => (
              <motion.li key={report.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.03 }}>
                <button onClick={() => handleSelect(report.id)} className="group flex w-full items-center gap-4 px-5 py-3.5 text-left hover:bg-cyan-500/5 transition-all">
                  <div className="flex h-8 w-8 items-center justify-center rounded-md bg-teal-500/10 border border-teal-500/20">
                    <FileText className="h-4 w-4 text-teal-400" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-200 group-hover:text-white transition-colors">{report.title}</p>
                    <p className="mt-0.5 font-mono text-[9px] text-gray-600">{report.report_type.replace(/_/g, ' ')}</p>
                  </div>
                  <span className="font-mono text-[9px] text-gray-700">{formatDate(report.created_at)}</span>
                  <div className="w-1 h-1 rounded-full bg-teal-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              </motion.li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
