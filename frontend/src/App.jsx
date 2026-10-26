import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import JobProgressModal from './components/JobProgressModal';
import ErrorBoundary from './components/ErrorBoundary';

import Overview from './pages/Overview';
import LiveUnlearningDemo from './pages/LiveUnlearningDemo';
import DatasetExplorer from './pages/DatasetExplorer';
import ModelTraining from './pages/ModelTraining';
import ForgettingRequest from './pages/ForgettingRequest';
import UnlearningLab from './pages/UnlearningLab';
import EvaluationDashboard from './pages/EvaluationDashboard';
import ExperimentHistory from './pages/ExperimentHistory';
import ResearchInsights from './pages/ResearchInsights';

import { api } from './services/api';

export default function App() {
  const [currentTab, setCurrentTab] = useState('overview');
  const [activeExperiment, setActiveExperiment] = useState(null);
  const [experimentsCount, setExperimentsCount] = useState(0);
  const [hardware, setHardware] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Background Job tracking
  const [activeJobId, setActiveJobId] = useState(null);
  const [activeJob, setActiveJob] = useState(null);
  const [showJobModal, setShowJobModal] = useState(false);

  // Initial load
  useEffect(() => {
    refreshAll();
  }, []);

  // Poll active job if one is running
  useEffect(() => {
    if (!activeJobId) return;

    let interval = setInterval(async () => {
      try {
        const job = await api.getJob(activeJobId);
        setActiveJob(job);

        // If job completed or failed
        if (job.status === 'COMPLETED' || job.status === 'FAILED') {
          clearInterval(interval);
          // Refresh active experiment state
          if (job.experiment_id) {
            const exp = await api.getExperiment(job.experiment_id);
            setActiveExperiment(exp);
          }
        }
      } catch (err) {
        console.error('Job polling error:', err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeJobId]);

  const refreshAll = async () => {
    setIsRefreshing(true);
    try {
      // Load health
      const h = await api.getHealth();
      setHardware(h.hardware);

      // Load experiments
      const exps = await api.listExperiments();
      setExperimentsCount(exps.length);

      if (exps.length > 0) {
        // If no active experiment or current one is updated, fetch latest
        const latestId = activeExperiment?.id || exps[0].id;
        const fullLatest = await api.getExperiment(latestId);
        setActiveExperiment(fullLatest);
      }
    } catch (err) {
      console.error('Failed to refresh app data:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleStartJob = (jobId) => {
    setActiveJobId(jobId);
    setShowJobModal(true);
  };

  const handleExperimentUpdated = (updatedExp) => {
    setActiveExperiment(updatedExp);
    setExperimentsCount((c) => Math.max(c, 1));
  };

  const isFileProtocol = typeof window !== 'undefined' && window.location.protocol === 'file:';

  return (
    <div className="flex h-screen bg-[#F4F4F0] text-black overflow-hidden font-sans bg-grid-pattern">
      {/* Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        activeExperiment={activeExperiment}
      />

      {/* Main Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {isFileProtocol && (
          <div className="bg-black text-acid px-4 py-2 text-xs font-mono flex items-center justify-between border-b border-black shrink-0">
            <span>SYS_NOTICE: Page opened via file:///. For full real-time API communication, please navigate to <strong>http://127.0.0.1:8000</strong>.</span>
          </div>
        )}

        <Navbar
          activeExperiment={activeExperiment}
          hardware={hardware}
          onRefresh={refreshAll}
          isRefreshing={isRefreshing}
        />

        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <ErrorBoundary>
            {currentTab === 'overview' && (
              <Overview
                onNavigate={setCurrentTab}
                activeExperiment={activeExperiment}
                experimentsCount={experimentsCount}
                hardware={hardware}
              />
            )}

            {currentTab === 'live-demo' && (
              <LiveUnlearningDemo />
            )}

            {currentTab === 'dataset' && (
              <DatasetExplorer selectedDataset={activeExperiment?.dataset_name || 'fashion_mnist'} />
            )}

            {currentTab === 'training' && (
              <ModelTraining
                activeExperiment={activeExperiment}
                onExperimentUpdated={handleExperimentUpdated}
                onStartJob={handleStartJob}
              />
            )}

            {currentTab === 'forgetting' && (
              <ForgettingRequest
                activeExperiment={activeExperiment}
                onExperimentUpdated={handleExperimentUpdated}
                onNavigate={setCurrentTab}
              />
            )}

            {currentTab === 'unlearning' && (
              <UnlearningLab
                activeExperiment={activeExperiment}
                onExperimentUpdated={handleExperimentUpdated}
                onStartJob={handleStartJob}
                onNavigate={setCurrentTab}
              />
            )}

            {currentTab === 'evaluation' && (
              <EvaluationDashboard
                activeExperiment={activeExperiment}
                onExperimentUpdated={handleExperimentUpdated}
                onStartJob={handleStartJob}
              />
            )}

            {currentTab === 'history' && (
              <ExperimentHistory
                activeExperiment={activeExperiment}
                onSelectExperiment={setActiveExperiment}
                onNavigate={setCurrentTab}
              />
            )}

            {currentTab === 'insights' && (
              <ResearchInsights activeExperiment={activeExperiment} />
            )}
          </ErrorBoundary>
        </main>
      </div>

      {/* Live Job Telemetry Modal */}
      {showJobModal && activeJob && (
        <JobProgressModal
          job={activeJob}
          onClose={() => setShowJobModal(false)}
        />
      )}
    </div>
  );
}

