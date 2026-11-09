import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function ProvenanceGraph() {
  const [authors, setAuthors] = useState([]);
  const [selectedAuthorId, setSelectedAuthorId] = useState('TOFU-000');
  const [graphData, setGraphData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadAuthors();
  }, []);

  useEffect(() => {
    if (selectedAuthorId) {
      loadGraph(selectedAuthorId);
    }
  }, [selectedAuthorId]);

  const loadAuthors = async () => {
    try {
      const list = await api.getTOFUAuthors(200, 0);
      setAuthors(list);
    } catch (err) {
      console.error('Failed to load authors:', err);
    }
  };

  const loadGraph = async (authorId) => {
    setIsLoading(true);
    try {
      const data = await api.getProvenanceGraph(authorId);
      setGraphData(data);
      if (data.nodes && data.nodes.length > 0) {
        setSelectedNode(data.nodes[2] || data.nodes[0]);
      }
    } catch (err) {
      console.error('Failed to load provenance graph:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    if (!status) return 'bg-neutral-100 text-neutral-800 border-neutral-300';
    if (status.includes('UNLEARNED') || status.includes('PURGED') || status.includes('REDACTED') || status.includes('ZEROED')) {
      return 'bg-red-50 text-red-700 border-red-500';
    }
    if (status.includes('ACTIVE') || status.includes('IMMUTABLE') || status.includes('PASS') || status.includes('TRAINED')) {
      return 'bg-emerald-50 text-emerald-800 border-emerald-500';
    }
    return 'bg-neutral-100 text-neutral-800 border-neutral-300';
  };

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="p-4 border border-black bg-white shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-sm font-bold tracking-wider">// DATA_LINEAGE & PROVENANCE GRAPH</div>
          <div className="text-neutral-500 text-[11px] mt-0.5">
            Full end-to-end trace from raw TOFU benchmark records to derived TF-IDF features, partitions, and PyTorch checkpoints.
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-neutral-500">AUTHOR_TARGET:</span>
          <select
            value={selectedAuthorId}
            onChange={(e) => setSelectedAuthorId(e.target.value)}
            className="bg-white border border-black px-2.5 py-1 text-xs font-bold focus:outline-none"
          >
            {authors.slice(0, 30).map((a) => (
              <option key={a.author_id} value={a.author_id}>
                [{a.author_id}] {a.author_name} ({a.cohort})
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading || !graphData ? (
        <div className="p-12 border border-black bg-white text-center">
          <div className="inline-block w-4 h-4 border-2 border-black border-t-transparent animate-spin mb-2"></div>
          <div>COMPILING PROVENANCE DAG...</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Visual DAG Flow */}
          <div className="lg:col-span-2 border border-black bg-white p-5 shadow-sm space-y-6">
            <div className="flex items-center justify-between pb-2 border-b border-black">
              <span className="font-bold">// DIRECTED_ACYCLIC_GRAPH (DAG)</span>
              <span className="text-[10px] text-neutral-500">{graphData.nodes?.length} NODES | {graphData.edges?.length} DIRECTED EDGES</span>
            </div>

            {/* Pipeline Stages */}
            <div className="space-y-4">
              {['BENCHMARK_SOURCE', 'COHORT_PARTITION', 'AUTHOR_RECORD', 'QA_PAIR', 'EMBEDDING_VECTOR', 'DATASET_PARTITION', 'CHECKPOINT', 'EVALUATION_METRIC'].map((stageKey) => {
                const stageNodes = (graphData.nodes || []).filter((n) => n.category === stageKey);
                if (stageNodes.length === 0) return null;

                return (
                  <div key={stageKey} className="p-3 bg-[#F8F9FA] border border-neutral-300 space-y-2">
                    <div className="text-[10px] text-neutral-500 font-bold uppercase tracking-wider">
                      STAGE: {stageKey.replace('_', ' ')}
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                      {stageNodes.map((node) => {
                        const isSelected = selectedNode?.id === node.id;
                        return (
                          <button
                            key={node.id}
                            onClick={() => setSelectedNode(node)}
                            className={`p-2.5 text-left border transition-all ${
                              isSelected
                                ? 'bg-black text-white border-black ring-1 ring-black'
                                : 'bg-white hover:border-black text-neutral-900 border-neutral-300'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className={`text-[9px] px-1 border uppercase font-bold ${getStatusBadge(node.status)}`}>
                                {node.status}
                              </span>
                            </div>
                            <div className="font-bold text-[11px] truncate">{node.label}</div>
                            <div className={`text-[10px] truncate mt-1 ${isSelected ? 'text-neutral-300' : 'text-neutral-500'}`}>
                              {node.details}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Node Inspector Panel */}
          <div className="border border-black bg-white p-5 shadow-sm space-y-4">
            <div className="pb-2 border-b border-black font-bold">// NODE_METADATA_INSPECTOR</div>

            {selectedNode ? (
              <div className="space-y-3">
                <div className="p-3 bg-neutral-900 text-white space-y-1">
                  <span className="text-[10px] text-acid font-bold">NODE_IDENTIFIER:</span>
                  <div className="font-bold text-xs truncate">{selectedNode.id}</div>
                </div>

                <div className="space-y-2 text-[11px]">
                  <div>
                    <span className="text-neutral-500 text-[10px]">LABEL:</span>
                    <div className="font-bold text-neutral-900 mt-0.5">{selectedNode.label}</div>
                  </div>
                  <div>
                    <span className="text-neutral-500 text-[10px]">CATEGORY:</span>
                    <div className="font-bold text-neutral-900 mt-0.5">{selectedNode.category}</div>
                  </div>
                  <div>
                    <span className="text-neutral-500 text-[10px]">CURRENT STATE:</span>
                    <div className="mt-0.5">
                      <span className={`px-1.5 py-0.5 border text-[10px] font-bold ${getStatusBadge(selectedNode.status)}`}>
                        {selectedNode.status}
                      </span>
                    </div>
                  </div>
                  <div>
                    <span className="text-neutral-500 text-[10px]">TECHNICAL DETAILS:</span>
                    <div className="p-2 bg-[#F8F9FA] border border-neutral-300 text-neutral-800 mt-0.5 leading-relaxed">
                      {selectedNode.details}
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-neutral-200">
                  <div className="text-[10px] text-neutral-500 font-bold uppercase mb-2">Connected Lineage Edges:</div>
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {(graphData.edges || [])
                      .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                      .map((edge, idx) => (
                        <div key={idx} className="p-1.5 bg-[#F8F9FA] border border-neutral-200 text-[10px] flex items-center justify-between">
                          <span className="truncate">{edge.source}</span>
                          <span className="text-neutral-400 mx-1">&rarr;</span>
                          <span className="truncate">{edge.target}</span>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-neutral-500 text-center py-12">Select a node from the DAG to inspect details.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
