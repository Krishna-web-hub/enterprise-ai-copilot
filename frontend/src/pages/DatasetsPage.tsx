/**
 * Datasets Page — Robotic Data Repository
 *
 * Matrix-style data grid with cyber upload zone, HUD detail views,
 * and neon-accented tables for the robotic AI aesthetic.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  Upload,
  FileSpreadsheet,
  FileText,
  Image,
  Trash2,
  ChevronLeft,
  AlertCircle,
  CheckCircle,
  X,
  Database,
  HardDrive,
  Rows3,
  Columns3,
  BarChart3,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  Dataset,
  uploadDataset,
  listDatasets,
  deleteDataset,
} from '../services/datasets';
import VisionAnalysisPanel from '../components/VisionAnalysisPanel';

function FileIcon({ type }: { type: string }) {
  switch (type) {
    case 'csv':
    case 'excel':
    case 'json':
      return <FileSpreadsheet className="h-4 w-4 text-neon-green" />;
    case 'pdf':
    case 'word':
    case 'text':
      return <FileText className="h-4 w-4 text-blue-400" />;
    case 'image':
      return <Image className="h-4 w-4 text-purple-400" />;
    default:
      return <FileText className="h-4 w-4 text-gray-500" />;
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

export default function DatasetsPage() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  useEffect(() => { loadDatasets(); }, []);

  async function loadDatasets() {
    setIsLoading(true);
    try {
      const response = await listDatasets(0, 50);
      setDatasets(response.datasets);
      setTotal(response.total);
    } catch { /* empty state */ }
    finally { setIsLoading(false); }
  }

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploadError(null);
    setUploadSuccess(null);
    setIsUploading(true);
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file) await uploadDataset(file);
      }
      const firstName = files[0]?.name ?? 'file';
      setUploadSuccess(files.length === 1 ? `"${firstName}" uploaded successfully` : `${files.length} files uploaded`);
      await loadDatasets();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setUploadError(axiosErr.response?.data?.detail || 'Upload failed');
      } else { setUploadError('Upload failed. Please try again.'); }
    } finally { setIsUploading(false); }
  }

  const handleDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragOver(true); }, []);
  const handleDragLeave = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragOver(false); }, []);
  const handleDrop = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragOver(false); handleUpload(e.dataTransfer.files); }, []);

  async function handleSelectDataset(dataset: Dataset) {
    // For structured datasets, go directly to the analytics dashboard
    if (['csv', 'excel', 'json'].includes(dataset.file_type)) {
      navigate(`/app/datasets/${dataset.id}/dashboard`);
      return;
    }
    // For other file types (PDF, images), show inline detail
    setSelectedDataset(dataset);
   
  }

  async function handleDelete(datasetId: number) {
    if (!confirm('Delete this dataset? This cannot be undone.')) return;
    try { await deleteDataset(datasetId); setSelectedDataset(null); await loadDatasets(); }
    catch { setUploadError('Failed to delete dataset'); }
  }

  // ─── Detail View ────────────────────────────────────────────
  if (selectedDataset) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <motion.button
            onClick={() => { setSelectedDataset(null); }}
            className="rounded-lg p-2 text-gray-500 hover:text-neon-blue hover:bg-cyber-400/10 border border-transparent hover:border-cyber-400/30 transition-all"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            aria-label="Back to datasets"
          >
            <ChevronLeft className="h-5 w-5" />
          </motion.button>
          <div className="flex-1">
            <h1 className="text-xl font-bold text-white">{selectedDataset.name}</h1>
            <p className="mt-0.5 font-mono text-[10px] text-gray-500 uppercase tracking-wider">
              {selectedDataset.file_type.toUpperCase()} // {formatFileSize(selectedDataset.file_size_bytes)} // {formatDate(selectedDataset.created_at)}
            </p>
          </div>
          {['csv', 'excel', 'json'].includes(selectedDataset.file_type) && (
            <button
              onClick={() => navigate(`/app/datasets/${selectedDataset.id}/dashboard`)}
              className="flex items-center gap-2 rounded-lg border border-cyber-400/30 bg-cyber-400/5 px-3 py-2 text-xs font-mono uppercase tracking-wider text-cyber-400 hover:bg-cyber-400/10 hover:border-cyber-400/50 transition-all"
            >
              <BarChart3 className="h-3.5 w-3.5" />
              Analytics
            </button>
          )}
          <button
            onClick={() => handleDelete(selectedDataset.id)}
            className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs font-mono uppercase tracking-wider text-red-400 hover:bg-red-500/20 hover:border-red-500/50 transition-all"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </button>
        </div>

        {/* Stats HUD */}
        {(selectedDataset.row_count !== null || selectedDataset.column_count !== null) && (
          <div className="grid grid-cols-3 gap-4">
            <div className="glass-panel p-4">
              <div className="flex items-center gap-2 mb-1">
                <Rows3 className="h-3.5 w-3.5 text-cyber-400/60" />
                <span className="hud-label">Rows</span>
              </div>
              <p className="font-mono text-xl font-bold text-white">{selectedDataset.row_count?.toLocaleString() ?? 'N/A'}</p>
            </div>
            <div className="glass-panel p-4">
              <div className="flex items-center gap-2 mb-1">
                <Columns3 className="h-3.5 w-3.5 text-purple-400/60" />
                <span className="hud-label">Columns</span>
              </div>
              <p className="font-mono text-xl font-bold text-white">{selectedDataset.column_count ?? 'N/A'}</p>
            </div>
            <div className="glass-panel p-4">
              <div className="flex items-center gap-2 mb-1">
                <HardDrive className="h-3.5 w-3.5 text-neon-green/60" />
                <span className="hud-label">Size</span>
              </div>
              <p className="font-mono text-xl font-bold text-white">{formatFileSize(selectedDataset.file_size_bytes)}</p>
            </div>
          </div>
        )}

        <VisionAnalysisPanel datasetId={selectedDataset.id} fileType={selectedDataset.file_type} />

        {/* Column metadata */}
        {selectedDataset.columns_metadata && selectedDataset.columns_metadata.length > 0 && (
          <div className="glass-panel overflow-hidden">
            <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
              <Database className="h-3.5 w-3.5 text-cyber-400/70" />
              <span className="hud-label">Column Schema</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-robot-border/20 bg-robot-darker/50">
                    <th className="px-5 py-2.5 text-left font-mono text-[10px] uppercase tracking-wider text-gray-500">Column</th>
                    <th className="px-5 py-2.5 text-left font-mono text-[10px] uppercase tracking-wider text-gray-500">Type</th>
                    <th className="px-5 py-2.5 text-left font-mono text-[10px] uppercase tracking-wider text-gray-500">Nulls</th>
                    <th className="px-5 py-2.5 text-left font-mono text-[10px] uppercase tracking-wider text-gray-500">Unique</th>
                    <th className="px-5 py-2.5 text-left font-mono text-[10px] uppercase tracking-wider text-gray-500">Samples</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedDataset.columns_metadata.map((col) => (
                    <tr key={col.name} className="border-b border-robot-border/10 hover:bg-cyber-400/5 transition-colors">
                      <td className="px-5 py-2.5 font-mono text-xs text-white">{col.name}</td>
                      <td className="px-5 py-2.5">
                        <span className="rounded-md bg-robot-darker border border-robot-border/30 px-2 py-0.5 font-mono text-[10px] text-cyber-400">
                          {col.dtype}
                        </span>
                      </td>
                      <td className="px-5 py-2.5 font-mono text-xs">
                        <span className={col.null_percent > 20 ? 'text-orange-400' : 'text-gray-400'}>
                          {col.null_count} ({col.null_percent}%)
                        </span>
                      </td>
                      <td className="px-5 py-2.5 font-mono text-xs text-gray-400">{col.unique_count}</td>
                      <td className="px-5 py-2.5 font-mono text-[10px] text-gray-500 max-w-48 truncate">
                        {col.sample_values.slice(0, 3).join(', ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
    );
  }

  // ─── List View ──────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Data Repository</h1>
        <p className="mt-1 font-mono text-[10px] text-gray-500 uppercase tracking-wider">
          Upload and manage data sources // CSV, Excel, JSON, PDF, Images
        </p>
      </div>

      {/* Notifications */}
      {uploadError && (
        <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-mono text-xs text-red-400">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span className="flex-1">{uploadError}</span>
          <button onClick={() => setUploadError(null)} aria-label="Dismiss"><X className="h-3.5 w-3.5" /></button>
        </div>
      )}
      {uploadSuccess && (
        <div className="flex items-center gap-3 rounded-lg border border-neon-green/30 bg-neon-green/10 px-4 py-3 font-mono text-xs text-neon-green">
          <CheckCircle className="h-4 w-4 flex-shrink-0" />
          <span className="flex-1">{uploadSuccess}</span>
          <button onClick={() => setUploadSuccess(null)} aria-label="Dismiss"><X className="h-3.5 w-3.5" /></button>
        </div>
      )}

      {/* Upload zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative rounded-xl border-2 border-dashed p-8 text-center transition-all duration-300 ${
          isDragOver
            ? 'border-neon-blue bg-cyber-400/5 shadow-neon'
            : 'border-robot-border/40 bg-robot-panel/30 hover:border-robot-border/60'
        }`}
      >
        <Upload className={`mx-auto h-8 w-8 ${isDragOver ? 'text-neon-blue' : 'text-gray-600'} transition-colors`} />
        <p className="mt-3 text-sm font-medium text-gray-300">
          {isUploading ? 'Processing upload...' : 'Drag and drop files here'}
        </p>
        <p className="mt-1 font-mono text-[10px] text-gray-600">or</p>
        <label className="btn-cyber-filled mt-3 inline-block cursor-pointer">
          Browse Files
          <input
            type="file"
            className="hidden"
            multiple
            accept=".csv,.xlsx,.xls,.json,.pdf,.docx,.doc,.png,.jpg,.jpeg,.gif,.txt"
            onChange={(e) => handleUpload(e.target.files)}
            disabled={isUploading}
          />
        </label>
        <p className="mt-3 font-mono text-[9px] text-gray-600 uppercase tracking-wider">
          Max 100MB per file
        </p>

        {isUploading && (
          <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-robot-dark/80 backdrop-blur-sm">
            <div className="flex items-center gap-3">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-neon-blue border-t-transparent" />
              <span className="font-mono text-xs text-gray-400">Processing data stream...</span>
            </div>
          </div>
        )}
      </div>

      {/* Dataset list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-neon-blue border-t-transparent" />
        </div>
      ) : datasets.length === 0 ? (
        <div className="glass-panel p-12 text-center">
          <FileSpreadsheet className="mx-auto h-10 w-10 text-gray-700" />
          <h3 className="mt-4 text-sm font-medium text-gray-400">No datasets in repository</h3>
          <p className="mt-1 font-mono text-[10px] text-gray-600">
            Upload your first file to initialize data analysis
          </p>
        </div>
      ) : (
        <div className="glass-panel overflow-hidden">
          <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
            <Database className="h-3.5 w-3.5 text-cyber-400/70" />
            <span className="hud-label">Repository Index</span>
            <span className="ml-auto font-mono text-[9px] text-gray-600">{total} entries</span>
          </div>
          <ul className="divide-y divide-robot-border/10" role="list">
            {datasets.map((dataset, idx) => (
              <motion.li
                key={dataset.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.03 }}
              >
                <button
                  onClick={() => handleSelectDataset(dataset)}
                  className="group flex w-full items-center gap-4 px-5 py-3.5 text-left transition-all duration-200 hover:bg-cyber-400/5"
                >
                  <span className="font-mono text-[9px] text-gray-700 w-5">{String(idx + 1).padStart(2, '0')}</span>
                  <div className="flex h-8 w-8 items-center justify-center rounded-md bg-robot-darker border border-robot-border/30">
                    <FileIcon type={dataset.file_type} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-200 group-hover:text-white transition-colors">{dataset.name}</p>
                    <p className="mt-0.5 font-mono text-[9px] text-gray-600">
                      {dataset.file_type.toUpperCase()} // {formatFileSize(dataset.file_size_bytes)}
                      {dataset.row_count !== null && <> // {dataset.row_count.toLocaleString()} rows</>}
                      {dataset.column_count !== null && <> // {dataset.column_count} cols</>}
                    </p>
                  </div>
                  <span className="font-mono text-[9px] text-gray-700">{formatDate(dataset.created_at)}</span>
                  <div className="w-1 h-1 rounded-full bg-cyber-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              </motion.li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

