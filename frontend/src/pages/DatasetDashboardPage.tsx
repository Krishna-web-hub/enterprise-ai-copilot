/**
 * DatasetDashboardPage
 *
 * Auto-generated analytics dashboard for a single dataset.
 * Shows: summary cards, data type breakdown, column stats,
 * distribution charts, correlation heatmap, null analysis, top values.
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ChevronLeft,
  Database,
  BarChart3,
  PieChart,
  Activity,
  AlertTriangle,
  Hash,
  Type,
  Calendar,
  Loader2,
  TrendingUp,
  Layers,
  Shield,
  Copy,
  Table,
  Trash2,
} from 'lucide-react';
import {
  DatasetAnalytics,
  NumericStats,
  getDatasetAnalytics,
  getDataset,
  getDatasetPreview,
  deleteDataset,
  Dataset,
  DatasetPreview,
} from '../services/datasets';
import { useTheme } from '../context/ThemeContext';
import clsx from 'clsx';

// ─── Simple Bar Chart (canvas-free, pure div-based) ───────────

function MiniBarChart({ bins, counts, color }: { bins: number[]; counts: number[]; color: string }) {
  const max = Math.max(...counts, 1);
  return (
    <div className="flex items-end gap-[2px] h-20">
      {counts.map((count, i) => (
        <div
          key={i}
          className="flex-1 rounded-t-sm transition-all duration-300 hover:opacity-80"
          style={{
            height: `${(count / max) * 100}%`,
            backgroundColor: color,
            minHeight: count > 0 ? '2px' : '0',
          }}
          title={`${bins[i]?.toFixed(1)} - ${bins[i + 1]?.toFixed(1)}: ${count}`}
        />
      ))}
    </div>
  );
}

// ─── Horizontal Bar (for top values) ──────────────────────────

function HorizontalBar({ value, count, percent, maxCount, color }: {
  value: string; count: number; percent: number; maxCount: number; color: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="font-mono text-[10px] text-gray-400 w-24 truncate" title={value}>{value}</span>
      <div className="flex-1 h-4 rounded-full bg-robot-border/20 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${(count / maxCount) * 100}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
      <span className="font-mono text-[9px] text-gray-500 w-12 text-right">{percent.toFixed(1)}%</span>
    </div>
  );
}

// ─── Correlation Heatmap ──────────────────────────────────────

function CorrelationHeatmap({ columns, matrix, isDark }: { columns: string[]; matrix: number[][]; isDark: boolean }) {
  function getColor(val: number): string {
    if (val > 0.7) return isDark ? '#00f0ff' : '#0891b2';
    if (val > 0.4) return isDark ? 'rgba(0,240,255,0.6)' : 'rgba(8,145,178,0.6)';
    if (val > 0.1) return isDark ? 'rgba(0,240,255,0.3)' : 'rgba(8,145,178,0.3)';
    if (val > -0.1) return isDark ? 'rgba(100,100,100,0.2)' : 'rgba(200,200,200,0.3)';
    if (val > -0.4) return isDark ? 'rgba(191,0,255,0.3)' : 'rgba(124,58,237,0.3)';
    if (val > -0.7) return isDark ? 'rgba(191,0,255,0.6)' : 'rgba(124,58,237,0.6)';
    return isDark ? '#bf00ff' : '#7c3aed';
  }

  return (
    <div className="overflow-x-auto">
      <div className="inline-block min-w-full">
        {/* Header row */}
        <div className="flex">
          <div className="w-20 flex-shrink-0" />
          {columns.map(col => (
            <div key={col} className="w-12 flex-shrink-0 text-center">
              <span className="font-mono text-[7px] text-gray-500 writing-mode-vertical" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>
                {col.slice(0, 8)}
              </span>
            </div>
          ))}
        </div>
        {/* Matrix rows */}
        {matrix.map((row, i) => (
          <div key={i} className="flex items-center">
            <div className="w-20 flex-shrink-0 pr-2 text-right">
              <span className="font-mono text-[8px] text-gray-500 truncate">{columns[i]?.slice(0, 10)}</span>
            </div>
            {row.map((val, j) => (
              <div
                key={j}
                className="w-12 h-8 flex-shrink-0 flex items-center justify-center border border-robot-border/10 rounded-sm"
                style={{ backgroundColor: getColor(val) }}
                title={`${columns[i]} × ${columns[j]}: ${val.toFixed(3)}`}
              >
                <span className="font-mono text-[7px] text-white/80">{val.toFixed(1)}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────

export default function DatasetDashboardPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const [analytics, setAnalytics] = useState<DatasetAnalytics | null>(null);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'analytics' | 'data'>('analytics');

  useEffect(() => {
    if (!id) return;
    loadAll(Number(id));
  }, [id]);

  async function loadAll(datasetId: number) {
    setIsLoading(true);
    setError(null);
    try {
      const [analyticsData, datasetData, previewData] = await Promise.all([
        getDatasetAnalytics(datasetId),
        getDataset(datasetId),
        getDatasetPreview(datasetId, 100),
      ]);
      setAnalytics(analyticsData);
      setDataset(datasetData);
      setPreview(previewData);
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setError(axiosErr.response?.data?.detail || 'Failed to load analytics');
      } else {
        setError('Failed to load analytics');
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDelete() {
    if (!id) return;
    if (!confirm('Delete this dataset? This cannot be undone.')) return;
    try {
      await deleteDataset(Number(id));
      navigate('/app/datasets');
    } catch { /* ignore */ }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-neon-blue" />
        <p className="font-mono text-xs text-gray-500 uppercase tracking-wider">Generating analytics dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <AlertTriangle className="h-8 w-8 text-red-400" />
        <p className="text-sm text-red-400">{error}</p>
        <button onClick={() => navigate('/app/datasets')} className="btn-cyber text-xs">Back to Datasets</button>
      </div>
    );
  }

  if (!analytics) return null;

  const numericCols = analytics.columns.filter(c => c.type === 'numeric');
  const categoricalCols = analytics.columns.filter(c => c.type === 'categorical');

  const chartColors = isDark
    ? ['#00f0ff', '#bf00ff', '#00ff88', '#ff6b00', '#3b82f6', '#f472b6']
    : ['#0891b2', '#7c3aed', '#059669', '#ea580c', '#2563eb', '#ec4899'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <motion.button
          onClick={() => navigate('/app/datasets')}
          className="rounded-lg p-2 text-gray-500 hover:text-neon-blue hover:bg-cyber-400/10 border border-transparent hover:border-cyber-400/30 transition-all"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
        >
          <ChevronLeft className="h-5 w-5" />
        </motion.button>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-white">{dataset?.name || analytics?.dataset_name}</h1>
          <p className="font-mono text-[10px] text-gray-500 uppercase tracking-wider">
            {dataset ? `${dataset.file_type.toUpperCase()} // ${(dataset.file_size_bytes / 1024 / 1024).toFixed(1)} MB // ${dataset.row_count?.toLocaleString() ?? '?'} rows` : 'Loading...'}
          </p>
        </div>
        <button
          onClick={handleDelete}
          className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs font-mono uppercase tracking-wider text-red-400 hover:bg-red-500/20 hover:border-red-500/50 transition-all"
        >
          <Trash2 className="h-3.5 w-3.5" /> Delete
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 rounded-lg bg-robot-panel/50 border border-robot-border/30 p-1 w-fit">
        <button
          onClick={() => setActiveTab('analytics')}
          className={clsx(
            'flex items-center gap-2 rounded-md px-4 py-2 font-mono text-xs transition-all',
            activeTab === 'analytics'
              ? 'bg-cyber-400/10 text-neon-blue border border-cyber-400/30'
              : 'text-gray-500 border border-transparent hover:text-gray-300'
          )}
        >
          <BarChart3 className="h-3.5 w-3.5" /> Analytics
        </button>
        <button
          onClick={() => setActiveTab('data')}
          className={clsx(
            'flex items-center gap-2 rounded-md px-4 py-2 font-mono text-xs transition-all',
            activeTab === 'data'
              ? 'bg-cyber-400/10 text-neon-blue border border-cyber-400/30'
              : 'text-gray-500 border border-transparent hover:text-gray-300'
          )}
        >
          <Table className="h-3.5 w-3.5" /> Data Preview
        </button>
      </div>

      {/* ─── DATA PREVIEW TAB ─── */}
      {activeTab === 'data' && preview && (
        <div className="glass-panel overflow-hidden">
          <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
            <Table className="h-3.5 w-3.5 text-neon-green/70" />
            <span className="hud-label">Data Preview</span>
            <span className="ml-auto font-mono text-[9px] text-gray-600">
              {preview.preview_rows} / {preview.total_rows.toLocaleString()} rows
            </span>
          </div>
          <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0">
                <tr className="border-b border-robot-border/20 bg-robot-darker/90">
                  <th className="px-3 py-2 text-left font-mono text-[9px] text-gray-600">#</th>
                  {preview.columns.map((col) => (
                    <th key={col} className="px-3 py-2 text-left font-mono text-[9px] uppercase tracking-wider text-gray-500">{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, rowIdx) => (
                  <tr key={rowIdx} className="border-b border-robot-border/10 hover:bg-cyber-400/5 transition-colors">
                    <td className="px-3 py-1.5 font-mono text-[9px] text-gray-700">{rowIdx + 1}</td>
                    {row.map((cell, colIdx) => (
                      <td key={colIdx} className="max-w-40 truncate px-3 py-1.5 font-mono text-[11px] text-gray-300">
                        {cell === null ? <span className="text-gray-700 italic">null</span> : String(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── ANALYTICS TAB ─── */}
      {activeTab === 'analytics' && analytics && (
        <>


      {/* ═══════ SUMMARY CARDS ═══════ */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {[
          { label: 'Rows', value: analytics.summary.row_count.toLocaleString(), icon: Layers, color: 'text-neon-blue' },
          { label: 'Columns', value: analytics.summary.column_count.toString(), icon: Database, color: 'text-purple-400' },
          { label: 'Quality', value: `${analytics.summary.data_quality_percent}%`, icon: Shield, color: analytics.summary.data_quality_percent > 90 ? 'text-neon-green' : 'text-orange-400' },
          { label: 'Nulls', value: analytics.summary.total_nulls.toLocaleString(), icon: AlertTriangle, color: 'text-orange-400' },
          { label: 'Duplicates', value: analytics.summary.duplicate_rows.toLocaleString(), icon: Copy, color: 'text-yellow-400' },
          { label: 'Memory', value: `${analytics.summary.memory_mb} MB`, icon: Activity, color: 'text-cyan-400' },
          { label: 'Numeric', value: `${analytics.data_types.numeric}/${analytics.summary.column_count}`, icon: Hash, color: 'text-blue-400' },
        ].map((card) => (
          <div key={card.label} className="glass-panel p-3">
            <div className="flex items-center gap-2 mb-1">
              <card.icon className={clsx('h-3.5 w-3.5', card.color)} />
              <span className="hud-label">{card.label}</span>
            </div>
            <p className="font-mono text-lg font-bold text-white">{card.value}</p>
          </div>
        ))}
      </div>

      {/* ═══════ DATA TYPES PIE ═══════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="glass-panel p-5">
          <div className="flex items-center gap-2 mb-4">
            <PieChart className="h-3.5 w-3.5 text-cyber-400/70" />
            <span className="hud-label">Column Types</span>
          </div>
          <div className="space-y-3">
            {[
              { label: 'Numeric', count: analytics.data_types.numeric, color: isDark ? '#00f0ff' : '#0891b2', icon: Hash },
              { label: 'Categorical', count: analytics.data_types.categorical, color: isDark ? '#bf00ff' : '#7c3aed', icon: Type },
              { label: 'Datetime', count: analytics.data_types.datetime, color: isDark ? '#00ff88' : '#059669', icon: Calendar },
              { label: 'Other', count: analytics.data_types.other, color: '#6b7280', icon: Database },
            ].filter(t => t.count > 0).map(t => (
              <div key={t.label} className="flex items-center gap-3">
                <t.icon className="h-3.5 w-3.5" style={{ color: t.color }} />
                <span className="text-xs text-gray-300 flex-1">{t.label}</span>
                <div className="w-24 h-2 rounded-full bg-robot-border/20 overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${(t.count / analytics.summary.column_count) * 100}%`, backgroundColor: t.color }} />
                </div>
                <span className="font-mono text-[10px] text-gray-500 w-6 text-right">{t.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ═══════ NULL ANALYSIS ═══════ */}
        <div className="glass-panel p-5 lg:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="h-3.5 w-3.5 text-orange-400/70" />
            <span className="hud-label">Missing Values</span>
            <span className="ml-auto font-mono text-[9px] text-gray-600">
              {analytics.null_analysis.length} columns with nulls
            </span>
          </div>
          {analytics.null_analysis.length === 0 ? (
            <p className="font-mono text-xs text-gray-500 text-center py-4">No missing values — perfect data quality!</p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {analytics.null_analysis.slice(0, 15).map((item) => (
                <div key={item.column} className="flex items-center gap-3">
                  <span className="font-mono text-[10px] text-gray-400 w-28 truncate" title={item.column}>{item.column}</span>
                  <div className="flex-1 h-3 rounded-full bg-robot-border/20 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-orange-400 to-red-400"
                      style={{ width: `${Math.min(item.null_percent, 100)}%` }}
                    />
                  </div>
                  <span className="font-mono text-[9px] text-gray-500 w-16 text-right">{item.null_percent}% ({item.null_count})</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ═══════ NUMERIC DISTRIBUTIONS ═══════ */}
      {numericCols.length > 0 && (
        <div className="glass-panel p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="h-3.5 w-3.5 text-neon-blue/70" />
            <span className="hud-label">Numeric Distributions</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {numericCols.filter(c => c.distribution).slice(0, 9).map((col, i) => {
              const stats = col.stats as NumericStats | undefined;
              return (
                <div key={col.name} className="rounded-lg border border-robot-border/20 bg-robot-darker/30 p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] text-gray-300 font-medium">{col.name}</span>
                    <span className="font-mono text-[8px] text-gray-600">{col.dtype}</span>
                  </div>
                  {col.distribution && (
                    <MiniBarChart
                      bins={col.distribution.bins}
                      counts={col.distribution.counts}
                      color={chartColors[i % chartColors.length]!}
                    />
                  )}
                  {stats && (
                    <div className="grid grid-cols-3 gap-1 mt-2 pt-2 border-t border-robot-border/10">
                      <div className="text-center">
                        <p className="font-mono text-[7px] text-gray-600">MEAN</p>
                        <p className="font-mono text-[9px] text-gray-300">{stats.mean?.toFixed(2)}</p>
                      </div>
                      <div className="text-center">
                        <p className="font-mono text-[7px] text-gray-600">STD</p>
                        <p className="font-mono text-[9px] text-gray-300">{stats.std?.toFixed(2)}</p>
                      </div>
                      <div className="text-center">
                        <p className="font-mono text-[7px] text-gray-600">MEDIAN</p>
                        <p className="font-mono text-[9px] text-gray-300">{stats.median?.toFixed(2)}</p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ═══════ CORRELATION HEATMAP ═══════ */}
      {analytics.correlations && analytics.correlations.columns.length >= 2 && (
        <div className="glass-panel p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-3.5 w-3.5 text-purple-400/70" />
            <span className="hud-label">Correlation Matrix</span>
            <span className="ml-auto font-mono text-[9px] text-gray-600">
              {analytics.correlations.columns.length} numeric columns
            </span>
          </div>
          <CorrelationHeatmap
            columns={analytics.correlations.columns}
            matrix={analytics.correlations.matrix}
            isDark={isDark}
          />
          <div className="flex items-center justify-center gap-4 mt-3 pt-2 border-t border-robot-border/10">
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: isDark ? '#bf00ff' : '#7c3aed' }} />
              <span className="font-mono text-[8px] text-gray-500">Negative</span>
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-sm bg-gray-500/30" />
              <span className="font-mono text-[8px] text-gray-500">None</span>
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: isDark ? '#00f0ff' : '#0891b2' }} />
              <span className="font-mono text-[8px] text-gray-500">Positive</span>
            </span>
          </div>
        </div>
      )}

      {/* ═══════ TOP VALUES (CATEGORICAL) ═══════ */}
      {categoricalCols.length > 0 && (
        <div className="glass-panel p-5">
          <div className="flex items-center gap-2 mb-4">
            <Type className="h-3.5 w-3.5 text-neon-purple/70" />
            <span className="hud-label">Categorical Columns — Top Values</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {categoricalCols.filter(c => c.top_values && c.top_values.length > 0).slice(0, 6).map((col, i) => {
              const maxCount = col.top_values![0]?.count ?? 1;
              return (
                <div key={col.name} className="rounded-lg border border-robot-border/20 bg-robot-darker/30 p-3">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-mono text-[10px] text-gray-300 font-medium">{col.name}</span>
                    <span className="font-mono text-[8px] text-gray-600">{col.unique_count} unique</span>
                  </div>
                  <div className="space-y-1.5">
                    {col.top_values!.slice(0, 5).map((tv) => (
                      <HorizontalBar
                        key={tv.value}
                        value={tv.value}
                        count={tv.count}
                        percent={tv.percent}
                        maxCount={maxCount}
                        color={chartColors[i % chartColors.length]!}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ═══════ COLUMN DETAIL TABLE ═══════ */}
      <div className="glass-panel overflow-hidden">
        <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
          <Database className="h-3.5 w-3.5 text-cyber-400/70" />
          <span className="hud-label">All Columns</span>
          <span className="ml-auto font-mono text-[9px] text-gray-600">{analytics.columns.length} columns</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-robot-border/20 bg-robot-darker/50">
                <th className="px-4 py-2.5 text-left font-mono text-[9px] uppercase tracking-wider text-gray-500">Column</th>
                <th className="px-4 py-2.5 text-left font-mono text-[9px] uppercase tracking-wider text-gray-500">Type</th>
                <th className="px-4 py-2.5 text-left font-mono text-[9px] uppercase tracking-wider text-gray-500">Dtype</th>
                <th className="px-4 py-2.5 text-left font-mono text-[9px] uppercase tracking-wider text-gray-500">Nulls</th>
                <th className="px-4 py-2.5 text-left font-mono text-[9px] uppercase tracking-wider text-gray-500">Unique</th>
                <th className="px-4 py-2.5 text-left font-mono text-[9px] uppercase tracking-wider text-gray-500">Stats</th>
              </tr>
            </thead>
            <tbody>
              {analytics.columns.map((col) => {
                const stats = col.type === 'numeric' ? col.stats as NumericStats | undefined : null;
                return (
                  <tr key={col.name} className="border-b border-robot-border/10 hover:bg-cyber-400/5 transition-colors">
                    <td className="px-4 py-2 font-mono text-[11px] text-white">{col.name}</td>
                    <td className="px-4 py-2">
                      <span className={clsx(
                        'rounded-md px-1.5 py-0.5 font-mono text-[9px] border',
                        col.type === 'numeric' ? 'text-blue-400 border-blue-400/30 bg-blue-400/10' :
                        col.type === 'categorical' ? 'text-purple-400 border-purple-400/30 bg-purple-400/10' :
                        col.type === 'datetime' ? 'text-green-400 border-green-400/30 bg-green-400/10' :
                        'text-gray-400 border-gray-400/30 bg-gray-400/10'
                      )}>
                        {col.type}
                      </span>
                    </td>
                    <td className="px-4 py-2 font-mono text-[10px] text-gray-500">{col.dtype}</td>
                    <td className="px-4 py-2 font-mono text-[10px]">
                      <span className={col.null_percent > 20 ? 'text-orange-400' : 'text-gray-400'}>
                        {col.null_percent}%
                      </span>
                    </td>
                    <td className="px-4 py-2 font-mono text-[10px] text-gray-400">{col.unique_count}</td>
                    <td className="px-4 py-2 font-mono text-[9px] text-gray-500">
                      {stats ? `μ=${stats.mean?.toFixed(1)} σ=${stats.std?.toFixed(1)}` : col.top_values ? `top: ${col.top_values[0]?.value}` : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      </>
      )}
    </div>
  );
}
