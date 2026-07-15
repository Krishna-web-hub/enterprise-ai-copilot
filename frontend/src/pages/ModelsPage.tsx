/**
 * Models Page — Neural Lab Aesthetic
 *
 * ML training and prediction interface styled as a robotic neural laboratory.
 * Metrics as HUD readouts, feature importance as neon bars.
 */

import { useEffect, useState } from 'react';
import {
  Brain,
  ChevronLeft,
  Trash2,
  Play,
  AlertCircle,
  CheckCircle,
  X,
  Sparkles,
  Cpu,
  Activity,
  Zap,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { Dataset, listDatasets } from '../services/datasets';
import {
  ModelDetail,
  ModelSummary,
  ModelType,
  PredictionResult,
  deleteModel,
  getModel,
  getSampleInput,
  listModels,
  predict,
  trainModel,
} from '../services/ml';

const STRUCTURED_TYPES = new Set(['csv', 'excel', 'json']);

const MODEL_TYPE_LABELS: Record<ModelType, string> = {
  classification: 'Classification',
  regression: 'Regression',
  clustering: 'Clustering',
  anomaly_detection: 'Anomaly Detection',
};

const ALGORITHM_OPTIONS: Record<ModelType, { value: string; label: string }[]> = {
  classification: [
    { value: '', label: 'Auto-select (recommended)' },
    { value: 'logistic_regression', label: 'Logistic Regression' },
    { value: 'random_forest', label: 'Random Forest' },
    { value: 'xgboost', label: 'XGBoost' },
    { value: 'lightgbm', label: 'LightGBM' },
  ],
  regression: [
    { value: '', label: 'Auto-select (recommended)' },
    { value: 'linear_regression', label: 'Linear Regression' },
    { value: 'random_forest', label: 'Random Forest' },
    { value: 'xgboost', label: 'XGBoost' },
    { value: 'lightgbm', label: 'LightGBM' },
  ],
  clustering: [{ value: '', label: 'K-Means (default)' }],
  anomaly_detection: [{ value: '', label: 'Isolation Forest (default)' }],
};

function formatMetricLabel(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ModelsPage() {
  const [models, setModels] = useState<ModelSummary[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(true);
  const [selectedModel, setSelectedModel] = useState<ModelDetail | null>(null);
  const [showTrainForm, setShowTrainForm] = useState(false);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useState<number | null>(null);
  const [modelType, setModelType] = useState<ModelType>('classification');
  const [targetColumn, setTargetColumn] = useState('');
  const [algorithm, setAlgorithm] = useState('');
  const [modelName, setModelName] = useState('');
  const [isTraining, setIsTraining] = useState(false);
  const [trainError, setTrainError] = useState<string | null>(null);
  const [trainSuccess, setTrainSuccess] = useState<string | null>(null);
  const [predictInputs, setPredictInputs] = useState<Record<string, string>>({});
  const [isPredicting, setIsPredicting] = useState(false);
  const [predictResults, setPredictResults] = useState<PredictionResult[] | null>(null);
  const [predictError, setPredictError] = useState<string | null>(null);

  useEffect(() => { loadModels(); }, []);

  async function loadModels() {
    setIsLoadingModels(true);
    try { const response = await listModels(0, 50); setModels(response.models); }
    catch { /* empty */ }
    finally { setIsLoadingModels(false); }
  }

  async function loadDatasetsForTraining() {
    try {
      const response = await listDatasets(0, 100);
      const queryable = response.datasets.filter((d) => STRUCTURED_TYPES.has(d.file_type));
      setDatasets(queryable);
      if (queryable.length > 0 && queryable[0]) setDatasetId(queryable[0].id);
    } catch { /* empty */ }
  }

  function openTrainForm() { setShowTrainForm(true); setTrainError(null); setTrainSuccess(null); loadDatasetsForTraining(); }

  const selectedDataset = datasets.find((d) => d.id === datasetId);
  const isSupervised = modelType === 'classification' || modelType === 'regression';

  async function handleTrain() {
    if (!datasetId) return;
    if (isSupervised && !targetColumn) { setTrainError('Target column required for this task.'); return; }
    setIsTraining(true); setTrainError(null); setTrainSuccess(null);
    try {
      const result = await trainModel({ dataset_id: datasetId, model_type: modelType, target_column: isSupervised ? targetColumn : null, algorithm: algorithm || null, name: modelName || null });
      setTrainSuccess(`"${result.name}" trained // ${result.algorithm}`);
      setShowTrainForm(false); setTargetColumn(''); setAlgorithm(''); setModelName('');
      await loadModels();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setTrainError(axiosErr.response?.data?.detail || 'Training failed');
      } else { setTrainError('Training failed'); }
    } finally { setIsTraining(false); }
  }

  async function handleSelectModel(modelId: number) {
    try {
      const detail = await getModel(modelId);
      setSelectedModel(detail);
      setPredictInputs(Object.fromEntries(detail.feature_columns.map((c) => [c, ''])));
      setPredictResults(null); setPredictError(null);
    } catch { /* stay on list */ }
  }

  async function handleDeleteModel(modelId: number) {
    if (!confirm('Delete this model?')) return;
    try { await deleteModel(modelId); setSelectedModel(null); await loadModels(); }
    catch { /* non-critical */ }
  }

  async function handlePredict() {
    if (!selectedModel) return;
    setIsPredicting(true); setPredictError(null); setPredictResults(null);
    try {
      const converted: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(predictInputs)) {
        const num = Number(value);
        converted[key] = value !== '' && !Number.isNaN(num) ? num : value;
      }
      const response = await predict(selectedModel.id, converted);
      setPredictResults(response.predictions);
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setPredictError(axiosErr.response?.data?.detail || 'Prediction failed');
      } else { setPredictError('Prediction failed'); }
    } finally { setIsPredicting(false); }
  }

  // ─── Detail View ────────────────────────────────────────────
  if (selectedModel) {
    const importanceEntries = selectedModel.feature_importance ? Object.entries(selectedModel.feature_importance) : [];
    const maxImportance = importanceEntries.length > 0 ? Math.max(...importanceEntries.map(([, v]) => v)) : 1;

    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <motion.button onClick={() => setSelectedModel(null)} className="rounded-lg p-2 text-gray-500 hover:text-neon-blue hover:bg-cyber-400/10 border border-transparent hover:border-cyber-400/30 transition-all" whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
            <ChevronLeft className="h-5 w-5" />
          </motion.button>
          <div className="flex-1">
            <h1 className="text-xl font-bold text-white">{selectedModel.name}</h1>
            <p className="mt-0.5 font-mono text-[10px] text-gray-500 uppercase tracking-wider">
              {MODEL_TYPE_LABELS[selectedModel.model_type]} // {selectedModel.algorithm}
              {selectedModel.target_column && <> // target: {selectedModel.target_column}</>}
            </p>
          </div>
          <button onClick={() => handleDeleteModel(selectedModel.id)} className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs font-mono uppercase text-red-400 hover:bg-red-500/20 transition-all">
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </button>
        </div>

        {/* Metrics HUD */}
        <div className="glass-panel overflow-hidden">
          <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
            <Activity className="h-3.5 w-3.5 text-neon-green/70" />
            <span className="hud-label">Performance Metrics</span>
          </div>
          <div className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-4">
            {Object.entries(selectedModel.metrics).map(([key, value]) => (
              <div key={key} className="rounded-lg border border-robot-border/20 bg-robot-darker/50 p-3">
                <p className="font-mono text-[9px] uppercase tracking-wider text-gray-500">{formatMetricLabel(key)}</p>
                <p className="mt-1 font-mono text-lg font-bold text-white">
                  {typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 4 }) : String(value)}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Feature importance */}
        {importanceEntries.length > 0 && (
          <div className="glass-panel overflow-hidden">
            <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
              <Zap className="h-3.5 w-3.5 text-purple-400/70" />
              <span className="hud-label">Feature Importance (SHAP)</span>
            </div>
            <div className="space-y-3 p-5">
              {importanceEntries.map(([feature, value]) => (
                <div key={feature}>
                  <div className="flex justify-between font-mono text-[10px]">
                    <span className="text-gray-300">{feature}</span>
                    <span className="text-gray-500">{value.toFixed(4)}</span>
                  </div>
                  <div className="mt-1 h-2 w-full rounded-full bg-robot-darker border border-robot-border/20 overflow-hidden">
                    <motion.div
                      className="h-full rounded-full bg-gradient-to-r from-purple-500 to-neon-blue"
                      initial={{ width: 0 }}
                      animate={{ width: `${(value / maxImportance) * 100}%` }}
                      transition={{ duration: 0.8, ease: 'easeOut' }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Predict */}
        <div className="glass-panel overflow-hidden">
          <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
            <Cpu className="h-3.5 w-3.5 text-cyber-400/70" />
            <span className="hud-label">Inference Terminal</span>
          </div>
          <div className="space-y-4 p-5">
            {/* Auto-fill button */}
            <div className="flex items-center gap-3">
              <motion.button
                onClick={async () => {
                  try {
                    const sample = await getSampleInput(selectedModel.id);
                    setPredictInputs(sample);
                  } catch (err) {
                    console.error('Failed to fetch sample:', err);
                    setPredictError('Could not load sample data');
                  }
                }}
                className="flex items-center gap-2 rounded-md border border-cyber-400/30 bg-cyber-400/5 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-cyber-400 hover:bg-cyber-400/10 hover:border-cyber-400/50 transition-all"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Sparkles className="h-3 w-3" />
                Fill with sample data
              </motion.button>
              <span className="font-mono text-[9px] text-gray-600">Auto-fills from your dataset</span>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {selectedModel.feature_columns.map((col) => (
                <div key={col}>
                  <label htmlFor={`feature-${col}`} className="hud-label mb-1 block">{col}</label>
                  <input id={`feature-${col}`} type="text" value={predictInputs[col] ?? ''} onChange={(e) => setPredictInputs((prev) => ({ ...prev, [col]: e.target.value }))} className="input-cyber" />
                </div>
              ))}
            </div>
            <motion.button onClick={handlePredict} disabled={isPredicting} className="btn-cyber-filled" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
              {isPredicting ? <><div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent mr-2 inline-block" />Processing...</> : <><Play className="h-4 w-4 mr-2 inline" />Run Prediction</>}
            </motion.button>

            {predictError && (
              <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-mono text-xs text-red-400">
                <AlertCircle className="h-4 w-4" />{predictError}
              </div>
            )}

            {predictResults && predictResults.length > 0 && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="rounded-lg border border-neon-green/20 bg-neon-green/5 p-4">
                {/* Show what the model is predicting */}
                <div className="flex items-center gap-2 mb-3 pb-2 border-b border-neon-green/10">
                  <Cpu className="h-3.5 w-3.5 text-neon-green/70" />
                  <span className="font-mono text-[10px] uppercase tracking-wider text-gray-400">
                    Predicting: <span className="text-neon-green">{selectedModel.target_column || 'target'}</span>
                  </span>
                  <span className="font-mono text-[9px] text-gray-600">|</span>
                  <span className="font-mono text-[9px] text-gray-600">
                    {MODEL_TYPE_LABELS[selectedModel.model_type]} // {selectedModel.algorithm}
                  </span>
                </div>
                {predictResults.map((r, idx) => (
                  <div key={idx} className={idx > 0 ? 'mt-3 border-t border-neon-green/10 pt-3' : ''}>
                    <p className="font-mono text-lg font-bold text-neon-green">
                      <span className="text-xs font-normal text-gray-400 mr-2">{selectedModel.target_column} =</span>
                      {String(r.prediction)}
                      {r.confidence !== null && (
                        <span className="ml-2 text-sm font-normal text-gray-400">({(r.confidence * 100).toFixed(1)}% confidence)</span>
                      )}
                    </p>
                    <p className="mt-1 text-xs text-gray-300">{r.explanation}</p>
                  </div>
                ))}
              </motion.div>
            )}
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
          <h1 className="text-2xl font-bold text-white">Neural Lab</h1>
          <p className="mt-1 font-mono text-[10px] text-gray-500 uppercase tracking-wider">
            Train, deploy, and monitor ML models
          </p>
        </div>
        <motion.button onClick={openTrainForm} className="btn-cyber-filled" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
          <Brain className="h-4 w-4 mr-2 inline" /> Train Model
        </motion.button>
      </div>

      {trainSuccess && (
        <div className="flex items-center gap-3 rounded-lg border border-neon-green/30 bg-neon-green/10 px-4 py-3 font-mono text-xs text-neon-green">
          <CheckCircle className="h-4 w-4" /><span className="flex-1">{trainSuccess}</span>
          <button onClick={() => setTrainSuccess(null)}><X className="h-3.5 w-3.5" /></button>
        </div>
      )}

      {/* Train form */}
      {showTrainForm && (
        <div className="glass-panel p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-neon-blue" />
              <span className="text-sm font-medium text-white">Initialize Training</span>
            </div>
            <button onClick={() => setShowTrainForm(false)}><X className="h-4 w-4 text-gray-500 hover:text-white transition-colors" /></button>
          </div>

          {datasets.length === 0 ? (
            <p className="font-mono text-xs text-gray-500">No structured datasets available. Upload data first.</p>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="hud-label mb-1 block">Dataset</label>
                <select value={datasetId ?? ''} onChange={(e) => { setDatasetId(Number(e.target.value)); setTargetColumn(''); }} className="input-cyber">
                  {datasets.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
              <div>
                <label className="hud-label mb-1 block">Task Type</label>
                <select value={modelType} onChange={(e) => { setModelType(e.target.value as ModelType); setAlgorithm(''); setTargetColumn(''); }} className="input-cyber">
                  {Object.entries(MODEL_TYPE_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
                </select>
              </div>
              {isSupervised && (
                <div>
                  <label className="hud-label mb-1 block">Target Column</label>
                  <select value={targetColumn} onChange={(e) => setTargetColumn(e.target.value)} className="input-cyber">
                    <option value="">Select column...</option>
                    {selectedDataset?.columns_metadata?.map((col) => <option key={col.name} value={col.name}>{col.name} ({col.dtype})</option>)}
                  </select>
                </div>
              )}
              <div>
                <label className="hud-label mb-1 block">Algorithm</label>
                <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value)} className="input-cyber">
                  {ALGORITHM_OPTIONS[modelType].map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="hud-label mb-1 block">Model Name (optional)</label>
                <input type="text" value={modelName} onChange={(e) => setModelName(e.target.value)} placeholder="e.g. Customer Churn Predictor" className="input-cyber" />
              </div>
              {trainError && (
                <div className="sm:col-span-2 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 font-mono text-xs text-red-400">
                  <AlertCircle className="h-4 w-4" />{trainError}
                </div>
              )}
              <div className="sm:col-span-2">
                <motion.button onClick={handleTrain} disabled={isTraining} className="btn-cyber-filled" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  {isTraining ? <><div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent mr-2 inline-block" />Training...</> : 'Execute Training'}
                </motion.button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Model list */}
      {isLoadingModels ? (
        <div className="flex justify-center py-12"><div className="h-6 w-6 animate-spin rounded-full border-2 border-neon-blue border-t-transparent" /></div>
      ) : models.length === 0 ? (
        <div className="glass-panel p-12 text-center">
          <Brain className="mx-auto h-10 w-10 text-gray-700" />
          <h3 className="mt-4 text-sm font-medium text-gray-400">No models deployed</h3>
          <p className="mt-1 font-mono text-[10px] text-gray-600">Train your first model to enable predictions</p>
        </div>
      ) : (
        <div className="glass-panel overflow-hidden">
          <div className="flex items-center gap-2 border-b border-robot-border/30 px-5 py-3">
            <Brain className="h-3.5 w-3.5 text-purple-400/70" />
            <span className="hud-label">Model Registry</span>
            <span className="ml-auto font-mono text-[9px] text-gray-600">{models.length} models</span>
          </div>
          <ul className="divide-y divide-robot-border/10">
            {models.map((m, idx) => (
              <motion.li key={m.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.03 }}>
                <button onClick={() => handleSelectModel(m.id)} className="group flex w-full items-center gap-4 px-5 py-3.5 text-left hover:bg-purple-500/5 transition-all">
                  <div className="flex h-8 w-8 items-center justify-center rounded-md bg-purple-500/10 border border-purple-500/20">
                    <Brain className="h-4 w-4 text-purple-400" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-200 group-hover:text-white transition-colors">{m.name}</p>
                    <p className="mt-0.5 font-mono text-[9px] text-gray-600">
                      {MODEL_TYPE_LABELS[m.model_type]} // {m.algorithm}
                    </p>
                  </div>
                  <span className="font-mono text-[9px] text-gray-700">{new Date(m.created_at).toLocaleDateString()}</span>
                  <div className="w-1 h-1 rounded-full bg-purple-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              </motion.li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
