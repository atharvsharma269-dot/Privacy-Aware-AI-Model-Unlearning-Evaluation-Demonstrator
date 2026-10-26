import React, { useState } from 'react';
import { PlayCircle, Cpu, Sliders, CheckCircle2, AlertCircle, RefreshCw, BarChart2 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from 'recharts';
import { api } from '../services/api';

export default function ModelTraining({ activeExperiment, onExperimentUpdated, onStartJob }) {
  const [datasetName, setDatasetName] = useState(activeExperiment?.dataset_name || 'fashion_mnist');
  const [modelType, setModelType] = useState(activeExperiment?.model_name || 'mlp');
  const [epochs, setEpochs] = useState(activeExperiment?.train_config?.epochs || 5);
  const [batchSize, setBatchSize] = useState(activeExperiment?.train_config?.batch_size || 64);
  const [learningRate, setLearningRate] = useState(activeExperiment?.train_config?.learning_rate || 0.001);
  const [subsampleSize, setSubsampleSize] = useState(activeExperiment?.train_config?.subsample_size || 5000);
  const [optimizer, setOptimizer] = useState('adam');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const isTrained = activeExperiment?.status !== 'CREATED' && activeExperiment?.original_checkpoint_path;

  const handleStartTraining = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      let expId = activeExperiment?.id;

      if (!expId) {
        const displayName = datasetName === 'tofu' ? 'TOFU Author' : datasetName === 'mnist' ? 'MNIST' : 'Fashion-MNIST';
        const newExp = await api.createExperiment({
          name: `${displayName} ${modelType.toUpperCase()} Training`,
          description: `Trained on ${displayName} with ${optimizer} lr=${learningRate}`,
          dataset_name: datasetName,
          model_name: modelType,
          seed: 42,
          train_config: {
            epochs: parseInt(epochs),
            batch_size: parseInt(batchSize),
            learning_rate: parseFloat(learningRate),
            optimizer,
            subsample_size: subsampleSize ? parseInt(subsampleSize) : null,
          },
        });
        expId = newExp.id;
        onExperimentUpdated(newExp);
      }

      const jobData = await api.trainOriginalModel(expId, {
        epochs: parseInt(epochs),
        batch_size: parseInt(batchSize),
        learning_rate: parseFloat(learningRate),
        optimizer,
        subsample_size: subsampleSize ? parseInt(subsampleSize) : null,
      });

      onStartJob(jobData.job_id);
    } catch (err) {
      setError(err.message || 'Failed to start model training');
    } finally {
      setIsSubmitting(false);
    }
  };

  const trainHistory = activeExperiment?.metrics?.original_model?.history || [];

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-10">
      {/* Header */}
      <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-md bg-teal-950 text-teal-200">
              STAGE A
            </span>
            <span className="text-xs text-teal-800 font-semibold uppercase tracking-wider font-mono">Baseline Neural Network</span>
          </div>
          <h2 className="text-xl font-bold text-teal-950 mt-1 font-serif">Train Original Model</h2>
          <p className="text-xs text-teal-700/80 mt-1 font-medium">
            Train a genuine neural network on the full training pool (Retain + Forget samples together). Checkpoints and telemetry will be recorded.
          </p>
        </div>

        {isTrained && (
          <div className="flex items-center space-x-2 bg-teal-100 border border-teal-300 text-teal-950 px-4 py-2 rounded-xl text-xs font-bold shadow-sm font-mono">
            <CheckCircle2 className="h-4 w-4 text-teal-800" />
            <span>CHECKPOINT: original.pt</span>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2 font-medium">
          <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Grid: Hyperparameters vs Convergence Curves */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Hyperparameters Card */}
        <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-5 lg:col-span-1">
          <h3 className="text-sm font-bold text-teal-950 flex items-center space-x-2">
            <Sliders className="h-4 w-4 text-teal-800" />
            <span>Hyperparameter Suite</span>
          </h3>

          <div className="space-y-4 text-xs">
            {/* Target Dataset */}
            <div>
              <label className="text-teal-950 block mb-1.5 font-bold">Research Benchmark Dataset:</label>
              <select
                value={datasetName}
                disabled={Boolean(activeExperiment?.id)}
                onChange={(e) => setDatasetName(e.target.value)}
                className="w-full bg-teal-50 border border-teal-850/20 rounded-xl px-3.5 py-2 text-teal-950 font-semibold focus:ring-2 focus:ring-teal-700 focus:outline-none disabled:opacity-70 shadow-sm"
              >
                <option value="fashion_mnist">Fashion-MNIST (Visual Apparel Benchmark)</option>
                <option value="tofu">TOFU (LocusLab Author Privacy Benchmark)</option>
                <option value="mnist">MNIST (Handwritten Digits)</option>
              </select>
            </div>

            {/* Model Architecture */}
            <div>
              <label className="text-teal-950 block mb-1.5 font-bold">Model Architecture:</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setModelType('mlp')}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    modelType === 'mlp'
                      ? 'border-teal-700 bg-teal-100/70 text-teal-950 shadow-sm'
                      : 'border-teal-850/15 bg-teal-50/60 text-teal-800 hover:border-teal-400'
                  }`}
                >
                  <div className="font-bold text-teal-950 text-xs font-mono">MLP Baseline</div>
                  <div className="text-[10px] text-teal-700 mt-0.5 font-medium">256-128 Dense layers</div>
                </button>
                <button
                  type="button"
                  onClick={() => setModelType('cnn')}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    modelType === 'cnn'
                      ? 'border-teal-700 bg-teal-100/70 text-teal-950 shadow-sm'
                      : 'border-teal-850/15 bg-teal-50/60 text-teal-800 hover:border-teal-400'
                  }`}
                >
                  <div className="font-bold text-teal-950 text-xs font-mono">CNN ConvNet</div>
                  <div className="text-[10px] text-teal-700 mt-0.5 font-medium">32-64 Conv filters</div>
                </button>
              </div>
            </div>

            {/* Epochs */}
            <div>
              <div className="flex justify-between mb-1.5">
                <label className="text-teal-950 font-bold">Training Epochs:</label>
                <span className="font-mono font-bold text-teal-800">{epochs}</span>
              </div>
              <input
                type="range"
                min="1"
                max="15"
                value={epochs}
                onChange={(e) => setEpochs(e.target.value)}
                className="w-full accent-teal-700 cursor-pointer"
              />
            </div>

            {/* Batch Size */}
            <div>
              <label className="text-teal-950 block mb-1.5 font-bold">Batch Size:</label>
              <select
                value={batchSize}
                onChange={(e) => setBatchSize(e.target.value)}
                className="w-full bg-teal-50 border border-teal-850/20 rounded-xl px-3.5 py-2 text-teal-950 font-medium focus:ring-2 focus:ring-teal-700 focus:outline-none"
              >
                <option value="32">32 samples / batch</option>
                <option value="64">64 samples / batch (Standard)</option>
                <option value="128">128 samples / batch</option>
              </select>
            </div>

            {/* Learning Rate */}
            <div>
              <label className="text-teal-950 block mb-1.5 font-bold">Learning Rate:</label>
              <select
                value={learningRate}
                onChange={(e) => setLearningRate(e.target.value)}
                className="w-full bg-teal-50 border border-teal-850/20 rounded-xl px-3.5 py-2 text-teal-950 font-medium font-mono focus:ring-2 focus:ring-teal-700 focus:outline-none"
              >
                <option value="0.002">0.002 (Fast convergence)</option>
                <option value="0.001">0.001 (Recommended Adam)</option>
                <option value="0.0005">0.0005 (Conservative)</option>
              </select>
            </div>

            {/* Subsampling for Rapid Demonstration */}
            <div>
              <label className="text-teal-950 block mb-1.5 font-bold">Dataset Pool Size:</label>
              <select
                value={subsampleSize}
                onChange={(e) => setSubsampleSize(e.target.value ? parseInt(e.target.value) : '')}
                className="w-full bg-teal-50 border border-teal-850/20 rounded-xl px-3.5 py-2 text-teal-950 font-medium focus:ring-2 focus:ring-teal-700 focus:outline-none"
              >
                <option value="3000">3,000 samples (Rapid Demo ~3s)</option>
                <option value="6000">6,000 samples (Balanced Demo ~8s)</option>
                <option value="15000">15,000 samples (Intermediate ~20s)</option>
                <option value="">60,000 samples (Full Pool)</option>
              </select>
            </div>
          </div>

          <button
            onClick={handleStartTraining}
            disabled={isSubmitting}
            className="w-full py-3.5 rounded-xl bg-teal-950 hover:bg-teal-900 text-white font-bold text-xs uppercase tracking-wider transition flex items-center justify-center space-x-2 shadow-tactile disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin text-teal-300" />
                <span>Initializing PyTorch Job...</span>
              </>
            ) : (
              <>
                <PlayCircle className="h-4 w-4 text-teal-300" />
                <span>{isTrained ? 'Retrain Original Model' : 'Start Model Training'}</span>
              </>
            )}
          </button>
        </div>

        {/* Right: Convergence Curves & Architectural Specs */}
        <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-6 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-teal-950 flex items-center space-x-2">
              <BarChart2 className="h-4 w-4 text-teal-800" />
              <span>Training Convergence & Telemetry</span>
            </h3>
            {isTrained && (
              <span className="text-xs text-teal-950 font-mono font-bold bg-teal-100 px-3 py-1 rounded-md border border-teal-300">
                Final Test Acc: {activeExperiment?.metrics?.original_model?.test?.accuracy}%
              </span>
            )}
          </div>

          {trainHistory.length > 0 ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trainHistory} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E8EFEA" />
                  <XAxis dataKey="epoch" stroke="#155B58" fontSize={11} label={{ value: 'Epoch', position: 'insideBottomRight', offset: -5 }} />
                  <YAxis stroke="#155B58" fontSize={11} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#073D3C',
                      borderColor: '#0B4B49',
                      borderRadius: '0.75rem',
                      color: '#E5F5F1',
                      fontSize: '12px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                  <Line type="monotone" dataKey="train_accuracy" name="Train Accuracy (%)" stroke="#3E8F89" strokeWidth={2.5} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="val_accuracy" name="Val Accuracy (%)" stroke="#073D3C" strokeWidth={2.5} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 border-2 border-dashed border-teal-850/20 rounded-2xl flex flex-col items-center justify-center text-teal-700 space-y-2 text-xs bg-teal-50/40">
              <PlayCircle className="h-10 w-10 text-teal-400" />
              <p className="font-semibold text-teal-950">No training telemetry available yet.</p>
              <p className="text-[11px] text-teal-700/80">Configure parameters and click "Start Model Training" on the left.</p>
            </div>
          )}

          {/* Model Architectural Specs */}
          <div className="p-5 rounded-2xl bg-teal-100/60 border border-teal-850/15 space-y-3">
            <h4 className="text-xs font-bold text-teal-950 uppercase tracking-wider font-mono">Architecture Specification</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div className="bg-white p-3 rounded-xl border border-teal-850/15">
                <span className="text-teal-700 block text-[10px] font-bold uppercase font-mono">Input Tensor</span>
                <span className="font-mono font-bold text-teal-950">1 × 28 × 28 (784)</span>
              </div>
              <div className="bg-white p-3 rounded-xl border border-teal-850/15">
                <span className="text-teal-700 block text-[10px] font-bold uppercase font-mono">Output Classes</span>
                <span className="font-mono font-bold text-teal-950">10 (Softmax)</span>
              </div>
              <div className="bg-white p-3 rounded-xl border border-teal-850/15">
                <span className="text-teal-700 block text-[10px] font-bold uppercase font-mono">Parameters</span>
                <span className="font-mono font-bold text-teal-900">
                  {modelType === 'mlp' ? '~235,146' : '~218,890'} weights
                </span>
              </div>
              <div className="bg-white p-3 rounded-xl border border-teal-850/15">
                <span className="text-teal-700 block text-[10px] font-bold uppercase font-mono">Regularization</span>
                <span className="font-mono font-bold text-teal-950">BatchNorm + Drop(0.2)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
