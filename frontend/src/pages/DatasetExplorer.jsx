import React, { useState, useEffect } from 'react';
import { Layers, Image as ImageIcon, Filter, RefreshCw, BarChart2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';
import { api } from '../services/api';

const TEAL_PALETTE = [
  '#073D3C', '#0B4B49', '#155B58', '#26736D', '#3E8F89',
  '#6CB5AC', '#9EDBD0', '#052E30', '#093F3E', '#1B6A65',
];

export default function DatasetExplorer({ selectedDataset = 'fashion_mnist' }) {
  const [datasetId, setDatasetId] = useState(selectedDataset);
  const [summary, setSummary] = useState(null);
  const [samples, setSamples] = useState([]);
  const [selectedClass, setSelectedClass] = useState(null);
  const [split, setSplit] = useState('train');
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);

  useEffect(() => {
    loadDatasetInfo();
  }, [datasetId]);

  useEffect(() => {
    loadSamples();
  }, [datasetId, split, selectedClass, page]);

  const loadDatasetInfo = async () => {
    try {
      const data = await api.getDatasetSummary(datasetId);
      setSummary(data);
    } catch (err) {
      console.error('Failed to load dataset summary:', err);
    }
  };

  const loadSamples = async () => {
    setLoading(true);
    try {
      const res = await api.getDatasetSamples(datasetId, {
        split,
        offset: page * 24,
        limit: 24,
        classFilter: selectedClass,
      });
      setSamples(res.samples || []);
    } catch (err) {
      console.error('Failed to load samples:', err);
    } finally {
      setLoading(false);
    }
  };

  const chartData = summary?.class_distribution_train
    ? Object.entries(summary.class_distribution_train).map(([name, count], index) => ({
        name,
        count,
        color: TEAL_PALETTE[index % TEAL_PALETTE.length],
      }))
    : [];

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-10">
      {/* Top Banner & Dataset Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-3xl bg-white border border-teal-850/15 shadow-tactile">
        <div>
          <h2 className="text-xl font-bold text-teal-950 flex items-center space-x-2 font-serif">
            <Layers className="h-5 w-5 text-teal-800" />
            <span>Dataset Explorer & Partition Inspector</span>
          </h2>
          <p className="text-xs text-teal-700/80 mt-1 font-medium">
            Browse real training and evaluation images, verify balanced distributions, and inspect class partitions.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <label className="text-xs font-bold text-teal-800/80 uppercase tracking-wider font-mono">Dataset:</label>
          <select
            value={datasetId}
            onChange={(e) => {
              setDatasetId(e.target.value);
              setSelectedClass(null);
              setPage(0);
            }}
            className="bg-teal-50 border border-teal-850/20 text-teal-950 text-xs font-semibold rounded-xl px-3.5 py-2 focus:ring-2 focus:ring-teal-700 focus:outline-none shadow-sm"
          >
            <option value="fashion_mnist">Fashion-MNIST (Visual Apparel Benchmark)</option>
            <option value="tofu">TOFU (LocusLab Author Privacy Benchmark)</option>
            <option value="mnist">MNIST (Handwritten Digits)</option>
          </select>
        </div>
      </div>

      {/* Stats Cards - Pale Aqua Panels with Dark Teal Accents */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-teal-100/70 border border-teal-800/15 shadow-tactile border-l-4 border-l-teal-950">
            <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider font-mono">Training Pool</span>
            <div className="text-2xl font-extrabold font-mono text-teal-950 mt-1">
              {summary.total_train.toLocaleString()}
            </div>
            <span className="text-[11px] text-teal-700/80 font-medium">28x28 Grayscale Tensors</span>
          </div>

          <div className="p-5 rounded-2xl bg-teal-100/70 border border-teal-800/15 shadow-tactile border-l-4 border-l-teal-800">
            <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider font-mono">Independent Test</span>
            <div className="text-2xl font-extrabold font-mono text-teal-950 mt-1">
              {summary.total_test.toLocaleString()}
            </div>
            <span className="text-[11px] text-teal-700/80 font-medium">Unseen Generalization</span>
          </div>

          <div className="p-5 rounded-2xl bg-teal-100/70 border border-teal-800/15 shadow-tactile border-l-4 border-l-teal-700">
            <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider font-mono">Categories</span>
            <div className="text-2xl font-extrabold font-mono text-teal-950 mt-1">{summary.num_classes}</div>
            <span className="text-[11px] text-teal-700/80 font-medium">Uniform Class Balances</span>
          </div>

          <div className="p-5 rounded-2xl bg-teal-100/70 border border-teal-800/15 shadow-tactile border-l-4 border-l-teal-600">
            <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider font-mono">Strategy</span>
            <div className="text-2xl font-extrabold font-mono text-teal-950 mt-1">10% Val</div>
            <span className="text-[11px] text-teal-700/80 font-medium">Strictly Disjoint Subsets</span>
          </div>
        </div>
      )}

      {/* Class Frequency Bar Chart */}
      {chartData.length > 0 && (
        <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-teal-950 flex items-center space-x-2">
              <BarChart2 className="h-4 w-4 text-teal-800" />
              <span>Training Class Frequency Distribution</span>
            </h3>
            <span className="text-xs text-teal-700 font-mono font-medium">6,000 samples / category</span>
          </div>
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E8EFEA" />
                <XAxis dataKey="name" stroke="#155B58" fontSize={11} angle={-25} textAnchor="end" interval={0} />
                <YAxis stroke="#155B58" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#073D3C',
                    borderColor: '#0B4B49',
                    borderRadius: '0.75rem',
                    color: '#E5F5F1',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Interactive Sample Gallery */}
      <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-2.5">
            <div className="h-8 w-8 rounded-xl bg-teal-100 flex items-center justify-center border border-teal-300/60">
              <ImageIcon className="h-4 w-4 text-teal-800" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-teal-950">Interactive Sample Gallery</h3>
              <span className="text-xs text-teal-700/80 font-mono">24 samples per page</span>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-xl bg-teal-100 p-1 border border-teal-850/15 text-xs font-semibold">
              <button
                onClick={() => { setSplit('train'); setPage(0); }}
                className={`px-3.5 py-1 rounded-lg transition ${
                  split === 'train' ? 'bg-teal-950 text-white shadow-sm' : 'text-teal-800 hover:text-teal-950'
                }`}
              >
                Train Split
              </button>
              <button
                onClick={() => { setSplit('test'); setPage(0); }}
                className={`px-3.5 py-1 rounded-lg transition ${
                  split === 'test' ? 'bg-teal-950 text-white shadow-sm' : 'text-teal-800 hover:text-teal-950'
                }`}
              >
                Test Split
              </button>
            </div>

            {summary?.classes && (
              <select
                value={selectedClass !== null ? selectedClass : ''}
                onChange={(e) => {
                  setSelectedClass(e.target.value === '' ? null : parseInt(e.target.value));
                  setPage(0);
                }}
                className="bg-teal-50 border border-teal-850/20 text-teal-950 text-xs font-semibold rounded-xl px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-teal-700 shadow-sm"
              >
                <option value="">All 10 Categories</option>
                {summary.classes.map((cls, idx) => (
                  <option key={idx} value={idx}>
                    Class {idx}: {cls}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {/* Gallery Grid */}
        {loading ? (
          <div className="h-48 flex items-center justify-center text-teal-700 space-x-2 text-xs">
            <RefreshCw className="h-4 w-4 animate-spin text-teal-800" />
            <span className="font-medium font-mono">Loading dataset representations...</span>
          </div>
        ) : datasetId === 'tofu' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {samples.map((item) => (
              <div
                key={item.index}
                className="p-4 rounded-2xl border border-teal-850/15 bg-teal-50/60 hover:border-teal-700 hover:bg-white hover:shadow-tactile transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-teal-950 text-teal-200">
                      #{item.index}
                    </span>
                    <span className="text-xs font-bold text-teal-900 truncate max-w-[180px]">
                      {item.class_name}
                    </span>
                  </div>
                  <div className="bg-white rounded-xl p-2.5 border border-teal-850/15 mb-2">
                    <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider block font-mono">Question:</span>
                    <p className="text-xs text-teal-950 font-medium line-clamp-2 mt-0.5">{item.question}</p>
                  </div>
                  <div className="bg-teal-100/70 rounded-xl p-2.5 border border-teal-300/60">
                    <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider block font-mono">Answer:</span>
                    <p className="text-xs text-teal-950 font-medium line-clamp-2 mt-0.5">{item.answer}</p>
                  </div>
                </div>
                <div className="mt-3 pt-2 border-t border-teal-850/10 flex items-center justify-between text-[11px] text-teal-700 font-mono">
                  <span>Author ID: {item.author_id ?? Math.floor(item.index / 20)}</span>
                  <span>784-dim TF-IDF</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
            {samples.map((item) => (
              <div
                key={item.index}
                className="p-2.5 rounded-2xl border border-teal-850/15 bg-teal-50/70 flex flex-col items-center hover:border-teal-600 hover:bg-white hover:shadow-tactile transition-all group"
              >
                <div className="w-16 h-16 rounded-xl overflow-hidden bg-white flex items-center justify-center border border-teal-850/15 shadow-sm group-hover:scale-105 transition-transform">
                  <img
                    src={item.image_base64}
                    alt={item.class_name}
                    className="w-14 h-14 object-contain filter invert opacity-90 contrast-125"
                  />
                </div>
                <span className="text-[10px] font-mono text-teal-700 mt-2 font-medium">#{item.index}</span>
                <span className="text-[11px] font-bold text-teal-950 truncate max-w-full text-center">
                  {item.class_name}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        <div className="flex items-center justify-between pt-4 border-t border-teal-850/15 text-xs">
          <span className="text-teal-700 font-mono font-medium">Page {page + 1}</span>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-4 py-1.5 rounded-xl bg-teal-100 hover:bg-teal-200 text-teal-900 font-semibold disabled:opacity-40 transition shadow-sm border border-teal-850/15"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              className="px-4 py-1.5 rounded-xl bg-teal-100 hover:bg-teal-200 text-teal-900 font-semibold transition shadow-sm border border-teal-850/15"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
