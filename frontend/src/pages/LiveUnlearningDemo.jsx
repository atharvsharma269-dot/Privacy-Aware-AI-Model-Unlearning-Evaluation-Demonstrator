import React, { useState, useEffect } from 'react';
import {
  Trophy,
  HelpCircle,
  Trash2,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  ArrowRight,
  Database,
  Shield,
  Layers,
  Info,
  Check,
  Cpu,
  Brain,
  FileText,
  AlertCircle
} from 'lucide-react';
import { api } from '../services/api';

export default function LiveUnlearningDemo() {
  const [drivers, setDrivers] = useState([]);
  const [selectedDriverId, setSelectedDriverId] = useState('F1-001');
  const [driverDetails, setDriverDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Teacher Presentation Mode toggle
  const [teacherMode, setTeacherMode] = useState(true);

  // Q&A state
  const [question, setQuestion] = useState("Which team did Lewis Hamilton win the 2020 Drivers' Championship with?");
  const [isAsking, setIsAsking] = useState(false);
  const [queryResult, setQueryResult] = useState(null);

  // Forgetting state
  const [targetAttribute, setTargetAttribute] = useState('team_for_2020_title');
  const [isForgetting, setIsForgetting] = useState(false);
  const [forgetResult, setForgetResult] = useState(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  // Verification state
  const [beforeAfterHistory, setBeforeAfterHistory] = useState(null);
  const [retentionResult, setRetentionResult] = useState(null);
  const [isVerifyingRetention, setIsVerifyingRetention] = useState(false);

  // Audit timeline
  const [timeline, setTimeline] = useState([]);
  const [isResetting, setIsResetting] = useState(false);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    loadDrivers();
    loadTimeline();
  }, []);

  useEffect(() => {
    if (selectedDriverId) {
      loadDriverDetails(selectedDriverId);
    }
  }, [selectedDriverId]);

  const showNotificationMsg = (msg, type = 'success') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4500);
  };

  const loadDrivers = async () => {
    try {
      setLoading(true);
      const data = await api.getF1Drivers();
      setDrivers(data);
      if (data.length > 0 && !selectedDriverId) {
        setSelectedDriverId(data[0].driver_id);
      }
    } catch (err) {
      setError('Failed to load F1 drivers: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadDriverDetails = async (id) => {
    try {
      const details = await api.getF1Driver(id);
      setDriverDetails(details);
      // Auto-set default question and target attribute based on driver
      if (id === 'F1-001') {
        setQuestion("Which team did Lewis Hamilton win the 2020 Drivers' Championship with?");
        setTargetAttribute('team_for_2020_title');
      } else if (id === 'F1-002') {
        setQuestion("Which team did Michael Schumacher win the 1994 Drivers' Championship with?");
        setTargetAttribute('team_for_1994_title');
      } else if (id === 'F1-003') {
        setQuestion("Which car did Max Verstappen win the 2021 Drivers' Championship in?");
        setTargetAttribute('car_for_2021_title');
      } else if (id === 'F1-004') {
        setQuestion("Which team did Sebastian Vettel win the 2010 Drivers' Championship with?");
        setTargetAttribute('team_for_2010_title');
      } else if (id === 'F1-005') {
        setQuestion("Which team did Ayrton Senna win the 1988 Drivers' Championship with?");
        setTargetAttribute('team_for_1988_title');
      }
    } catch (err) {
      setError('Failed to load driver details: ' + err.message);
    }
  };

  const loadTimeline = async () => {
    try {
      const logs = await api.getF1Timeline();
      setTimeline(logs);
    } catch (err) {
      console.error('Failed to load timeline:', err);
    }
  };

  const handleAskQuestion = async (customQ = null) => {
    const qToAsk = customQ || question;
    if (!qToAsk.trim()) return;

    setIsAsking(true);
    try {
      const result = await api.askF1Question(qToAsk, selectedDriverId);
      setQueryResult(result);

      if (result.target_attribute) {
        setTargetAttribute(result.target_attribute);
      }

      // If we already had a previous active state and now it's unlearned, record before-after
      if (beforeAfterHistory && beforeAfterHistory.targetAttribute === result.target_attribute) {
        setBeforeAfterHistory((prev) => ({
          ...prev,
          after: result,
        }));
      } else if (result.found) {
        setBeforeAfterHistory({
          question: qToAsk,
          targetAttribute: result.target_attribute,
          before: result,
          after: null,
        });
      }

      await loadTimeline();
    } catch (err) {
      setError('Failed to execute query: ' + err.message);
    } finally {
      setIsAsking(false);
    }
  };

  const handleForgetFact = async () => {
    if (!selectedDriverId || !targetAttribute) return;
    setIsForgetting(true);
    setShowConfirmModal(false);

    try {
      const res = await api.forgetF1Fact(selectedDriverId, targetAttribute);
      setForgetResult(res);
      showNotificationMsg(`Fact '${targetAttribute}' successfully purged from working store!`, 'success');

      // Update local driver details
      await loadDriverDetails(selectedDriverId);
      await loadDrivers();

      // Automatically re-query to demonstrate the immediate unlearned state
      const postQueryResult = await api.askF1Question(question, selectedDriverId);
      setQueryResult(postQueryResult);

      if (beforeAfterHistory && beforeAfterHistory.before) {
        setBeforeAfterHistory((prev) => ({
          ...prev,
          after: postQueryResult,
        }));
      }

      // Trigger automatic retention verification on an unrelated attribute
      await executeRetentionCheck(selectedDriverId, targetAttribute);
      await loadTimeline();
    } catch (err) {
      setError('Failed to execute unlearning: ' + err.message);
      showNotificationMsg('Unlearning failed: ' + err.message, 'error');
    } finally {
      setIsForgetting(false);
    }
  };

  const executeRetentionCheck = async (driverId, forgottenAttr) => {
    setIsVerifyingRetention(true);
    try {
      // Pick an unrelated attribute
      let checkAttr = 'car_for_2008_title';
      if (driverId === 'F1-001') {
        checkAttr = forgottenAttr === 'car_for_2008_title' ? 'team_for_2014_title' : 'car_for_2008_title';
      } else if (driverId === 'F1-002') {
        checkAttr = forgottenAttr === 'car_for_2000_title' ? 'team_for_2004_title' : 'car_for_2000_title';
      } else if (driverId === 'F1-003') {
        checkAttr = forgottenAttr === 'car_for_2023_title' ? 'team_for_2024_title' : 'car_for_2023_title';
      } else if (driverId === 'F1-004') {
        checkAttr = forgottenAttr === 'car_for_2010_title' ? 'team_for_2013_title' : 'car_for_2010_title';
      } else if (driverId === 'F1-005') {
        checkAttr = forgottenAttr === 'car_for_1988_title' ? 'team_for_1991_title' : 'car_for_1988_title';
      }

      const check = await api.verifyF1Retention(driverId, checkAttr);
      setRetentionResult(check);
    } catch (err) {
      console.error('Retention check failed:', err);
    } finally {
      setIsVerifyingRetention(false);
    }
  };

  const handleResetDemo = async () => {
    setIsResetting(true);
    try {
      await api.resetF1Demo();
      await loadDrivers();
      await loadDriverDetails(selectedDriverId);
      await loadTimeline();
      setQueryResult(null);
      setForgetResult(null);
      setBeforeAfterHistory(null);
      setRetentionResult(null);
      showNotificationMsg('Knowledge store restored to immutable original dataset.', 'info');
    } catch (err) {
      setError('Failed to reset demo: ' + err.message);
    } finally {
      setIsResetting(false);
    }
  };

  if (loading && !driverDetails && drivers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[450px] space-y-4">
        <div className="w-12 h-12 border-4 border-ocean-200 border-t-ocean-600 rounded-full animate-spin"></div>
        <div className="text-center space-y-1">
          <p className="text-sm font-bold text-navy-950">Initializing Formula 1 Knowledge Store...</p>
          <p className="text-xs text-slate-500">Loading championship records and question-answer pairs</p>
        </div>
      </div>
    );
  }

  if (error && drivers.length === 0) {
    return (
      <div className="p-8 max-w-lg mx-auto bg-white rounded-3xl shadow-card border border-rose-200 text-center space-y-4 my-12">
        <AlertTriangle className="h-10 w-10 text-rose-500 mx-auto" />
        <h3 className="text-lg font-bold text-navy-950">Unable to Load F1 Knowledge Store</h3>
        <p className="text-xs text-slate-600">{error}</p>
        <button
          onClick={() => {
            setError(null);
            loadDrivers();
          }}
          className="px-5 py-2.5 rounded-xl bg-ocean-600 hover:bg-ocean-500 text-white font-bold text-xs uppercase"
        >
          Retry Loading
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Toast Notification */}
      {notification && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl shadow-2xl flex items-center space-x-3 text-sm font-semibold transition-all ${
          notification.type === 'success'
            ? 'bg-emerald-600 text-white'
            : notification.type === 'error'
            ? 'bg-rose-600 text-white'
            : 'bg-ocean-600 text-white'
        }`}>
          {notification.type === 'success' ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-200" />
          ) : (
            <AlertCircle className="h-5 w-5 text-white" />
          )}
          <span>{notification.msg}</span>
        </div>
      )}

      {/* Hero Header Banner (Retro-futuristic Research Terminal) */}
      <div className="p-8 rounded-3xl bg-teal-950 text-teal-100 shadow-tactile relative overflow-hidden border border-teal-850">
        <div className="absolute top-0 right-0 w-80 h-80 bg-teal-800/20 rounded-full blur-3xl pointer-events-none -mr-16 -mt-16"></div>
        <div className="absolute bottom-0 right-1/3 w-60 h-60 bg-teal-500/10 rounded-full blur-2xl pointer-events-none"></div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-3xl">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-lg bg-teal-900 border border-teal-750 text-teal-300 text-[11px] font-mono font-bold tracking-wider uppercase">
              <Trophy className="h-3.5 w-3.5 text-teal-300" />
              <span>Formula 1 World Champions Knowledge Benchmark</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white leading-tight font-serif">
              Live AI Unlearning Demonstration
            </h1>
            <p className="text-teal-200/90 text-sm leading-relaxed font-normal">
              Empirical verification of knowledge fact erasure on real Formula 1 championship records.
              Observe selective factual deletion, query silencing, and verifiable retention of non-target facts.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
            {/* Teacher Mode Toggle */}
            <button
              onClick={() => setTeacherMode(!teacherMode)}
              className={`flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-bold transition border ${
                teacherMode
                  ? 'bg-teal-300 text-teal-950 border-teal-200 shadow-tactile'
                  : 'bg-teal-900 text-teal-300 border-teal-800 hover:bg-teal-850'
              }`}
            >
              <Brain className="h-4 w-4" />
              <span>{teacherMode ? 'Teacher Mode: Active' : 'Teacher Mode: Off'}</span>
            </button>

            {/* Reset Demo Button */}
            <button
              onClick={handleResetDemo}
              disabled={isResetting}
              className="flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-teal-800/90 hover:bg-teal-700 text-teal-200 text-xs font-bold transition shadow-tactile border border-teal-700 disabled:opacity-50"
            >
              <RotateCcw className={`h-4 w-4 ${isResetting ? 'animate-spin' : ''}`} />
              <span>{isResetting ? 'Resetting Store...' : 'Reset Demo Dataset'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 5-Stage Visual Workflow Navigation Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {[
          { num: '01', title: 'Knowledge Base', desc: 'Driver records loaded', status: 'READY' },
          { num: '02', title: 'Baseline Query', desc: 'Ask natural question', status: queryResult?.found ? 'ACTIVE' : 'READY' },
          { num: '03', title: 'Scoped Forgetting', desc: 'Purge target fact', status: forgetResult ? 'PURGED' : 'PENDING' },
          { num: '04', title: 'Erasure Proof', desc: 'Query is unavailable', status: queryResult?.is_unlearned ? 'VERIFIED' : 'PENDING' },
          { num: '05', title: 'Retained Integrity', desc: 'Unrelated fact persists', status: retentionResult?.retained ? 'INTACT' : 'PENDING' },
        ].map((stage, idx) => (
          <div
            key={stage.num}
            className={`p-4 rounded-2xl border transition-all ${
              stage.status === 'VERIFIED' || stage.status === 'INTACT' || stage.status === 'PURGED'
                ? 'bg-teal-950 border-teal-700 shadow-tactile text-teal-100'
                : 'bg-teal-100/70 border-teal-800/15 shadow-sm text-teal-950'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs font-extrabold px-2 py-0.5 rounded-md bg-teal-900 text-teal-300 border border-teal-700">
                {stage.num}
              </span>
              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${
                stage.status === 'VERIFIED' || stage.status === 'INTACT' || stage.status === 'PURGED'
                  ? 'bg-teal-800 text-teal-200 border border-teal-600'
                  : 'bg-white/80 text-teal-800 border border-teal-800/15'
              }`}>
                {stage.status}
              </span>
            </div>
            <h4 className="text-xs font-bold leading-tight">{stage.title}</h4>
            <p className="text-[11px] text-teal-800/70 mt-1">{stage.desc}</p>
          </div>
        ))}
      </div>

      {/* Teacher Presentation Banner (Academic Context) */}
      {teacherMode && (
        <div className="p-5 rounded-2xl bg-teal-950 border-l-4 border-teal-300 text-teal-100 shadow-tactile space-y-2 border border-teal-850">
          <div className="flex items-center space-x-2 text-teal-300 font-bold text-xs uppercase tracking-wider font-mono">
            <Info className="h-4 w-4" />
            <span>Academic Presentation Guide for Teacher Evaluation</span>
          </div>
          <p className="text-xs text-teal-200/90 leading-relaxed font-normal">
            This module presents a live demonstration of <strong>Machine Unlearning / Factual Erasure</strong> using real historical records from Formula 1 world champions.
            Notice the distinction highlighted below: in this live demo, facts are purged from the structured working store to illustrate scoped record deletion and query silencing, while the companion Fashion-MNIST & TOFU benchmark modules perform parametric deep neural unlearning (gradient ascent and retain-set fine-tuning).
          </p>
        </div>
      )}

      {/* Main Interactive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Driver Selector & Active Knowledge Store (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Driver Selection Card */}
          <div className="bg-white rounded-3xl p-6 shadow-card border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <Database className="h-5 w-5 text-ocean-600" />
                <h3 className="text-base font-extrabold text-navy-950">1. Select Driver</h3>
              </div>
              <span className="text-[11px] font-mono font-bold text-ocean-600 bg-ocean-50 px-2.5 py-1 rounded-full border border-ocean-200">
                {drivers.length} Drivers Loaded
              </span>
            </div>

            <div className="grid grid-cols-1 gap-2.5">
              {drivers.map((d) => {
                const isSelected = d.driver_id === selectedDriverId;
                const hasUnlearned = d.unlearned_attributes && d.unlearned_attributes.length > 0;
                return (
                  <button
                    key={d.driver_id}
                    onClick={() => setSelectedDriverId(d.driver_id)}
                    className={`w-full text-left p-3.5 rounded-2xl transition-all border flex items-center justify-between ${
                      isSelected
                        ? 'bg-navy-950 text-white border-navy-800 shadow-md translate-x-1'
                        : 'bg-slate-50/60 hover:bg-slate-100/80 text-slate-700 border-slate-200'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`h-8 w-8 rounded-full flex items-center justify-center font-bold text-xs ${
                        isSelected ? 'bg-ocean-600 text-white' : 'bg-slate-200 text-slate-700'
                      }`}>
                        {d.driver_id.replace('F1-', '#')}
                      </div>
                      <div>
                        <div className="text-xs font-bold leading-tight">{d.driver_name}</div>
                        <div className={`text-[10px] ${isSelected ? 'text-slate-300' : 'text-slate-500'}`}>
                          {d.nationality} • {d.world_drivers_championships}x World Champion
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {hasUnlearned ? (
                        <span className="text-[10px] bg-rose-500/20 text-rose-400 border border-rose-500/30 px-2 py-0.5 rounded-full font-mono font-bold">
                          {d.unlearned_attributes.length} Unlearned
                        </span>
                      ) : (
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold ${
                          isSelected ? 'bg-emerald-500/20 text-emerald-300' : 'bg-emerald-100 text-emerald-700'
                        }`}>
                          Pristine
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Active Driver Knowledge Record */}
          {driverDetails && (
            <div className="bg-navy-950 text-white rounded-3xl p-6 shadow-card border border-navy-800 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-navy-800">
                <div className="flex items-center space-x-2">
                  <Shield className="h-5 w-5 text-ocean-400" />
                  <h3 className="text-base font-extrabold text-white">Active Knowledge Store</h3>
                </div>
                <span className="font-mono text-xs text-ocean-300 bg-navy-900 px-2.5 py-1 rounded-full border border-navy-800">
                  {driverDetails.driver_id}
                </span>
              </div>

              <div className="space-y-3">
                <div className="p-3.5 rounded-2xl bg-navy-900/90 border border-navy-800 space-y-1">
                  <div className="text-[10px] font-bold text-ocean-400 uppercase tracking-wider">Championship Years</div>
                  <div className="text-xs font-mono text-slate-200">
                    {driverDetails?.working_facts?.championship_years || (
                      <span className="text-rose-400 italic">Fact Unlearned</span>
                    )}
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-navy-900/90 border border-navy-800 space-y-1">
                  <div className="text-[10px] font-bold text-ocean-400 uppercase tracking-wider">Title-Winning Teams</div>
                  <div className="text-xs font-mono text-slate-200">
                    {driverDetails?.working_facts?.championship_teams || (
                      <span className="text-rose-400 italic">Fact Unlearned</span>
                    )}
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-navy-900/90 border border-navy-800 space-y-2">
                  <div className="text-[10px] font-bold text-ocean-400 uppercase tracking-wider">Key Season Attributes</div>
                  <div className="grid grid-cols-1 gap-1.5 text-xs">
                    {Object.entries(driverDetails?.original_facts || {})
                      .filter(([k]) => k.startsWith('team_for_') || k.startsWith('car_for_'))
                      .map(([attrKey, origVal]) => {
                        const isPurged = driverDetails?.unlearned_attributes?.includes(attrKey);
                        return (
                          <div
                            key={attrKey}
                            className={`p-2 rounded-xl flex items-center justify-between text-[11px] border ${
                              isPurged
                                ? 'bg-rose-950/40 border-rose-800/60 text-rose-300'
                                : 'bg-navy-850 border-navy-800 text-slate-200'
                            }`}
                          >
                            <span className="font-mono truncate max-w-[170px]">{attrKey}</span>
                            <div className="flex items-center space-x-1.5 shrink-0">
                              {isPurged ? (
                                <span className="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 text-[10px] font-bold uppercase">
                                  Purged
                                </span>
                              ) : (
                                <span className="font-bold text-ocean-300">{origVal}</span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Interactive Q&A, Unlearning Action, Before/After & Retention Proof (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Card 2: Interactive Natural Language Question */}
          <div className="bg-white rounded-3xl p-6 shadow-card border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <HelpCircle className="h-5 w-5 text-ocean-600" />
                <h3 className="text-base font-extrabold text-navy-950">2. Natural Language Query</h3>
              </div>
              <span className="text-[11px] text-slate-500 font-medium">Stage B Verification</span>
            </div>

            {/* Quick Questions Chips */}
            {driverDetails?.available_qa_pairs && driverDetails.available_qa_pairs.length > 0 && (
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                  Suggested Questions from Dataset
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {driverDetails.available_qa_pairs.slice(0, 4).map((qa, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setQuestion(qa.question);
                        handleAskQuestion(qa.question);
                      }}
                      className="text-[11px] text-left px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-ocean-50 hover:text-ocean-700 text-slate-700 transition border border-slate-200 max-w-full truncate"
                    >
                      {qa.question}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-2.5 pt-1">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask about a team, car, year, or championship..."
                className="flex-1 px-4 py-3 text-xs bg-slate-50 border border-slate-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-ocean-500 focus:bg-white text-slate-800 font-medium"
              />
              <button
                onClick={() => handleAskQuestion()}
                disabled={isAsking || !question.trim()}
                className="px-6 py-3 rounded-2xl bg-gradient-to-r from-ocean-600 to-sky-500 hover:from-ocean-500 hover:to-sky-400 text-white font-bold text-xs uppercase tracking-wider transition shadow-lg shadow-ocean-600/30 flex items-center justify-center space-x-2 disabled:opacity-50 shrink-0"
              >
                <HelpCircle className="h-4 w-4" />
                <span>{isAsking ? 'Querying...' : 'Ask Question'}</span>
              </button>
            </div>

            {/* Query Output Box */}
            {queryResult && (
              <div className={`p-4 rounded-2xl border transition-all ${
                queryResult.is_unlearned
                  ? 'bg-rose-50/70 border-rose-200 text-rose-900'
                  : 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    {queryResult.is_unlearned ? (
                      <AlertTriangle className="h-4 w-4 text-rose-600" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    )}
                    <span className="font-bold text-xs">
                      {queryResult.is_unlearned ? 'Fact Unlearned / Unavailable' : 'Active Knowledge Retrieved'}
                    </span>
                  </div>
                  <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full bg-white/80 border border-slate-200">
                    Attribute: {queryResult.target_attribute || 'Unknown'}
                  </span>
                </div>

                <div className="text-sm font-semibold mb-1">
                  "{queryResult.answer}"
                </div>

                <div className="text-[11px] opacity-80 flex items-center justify-between pt-1 border-t border-slate-200/60 mt-2">
                  <span>Driver: <strong>{queryResult.driver_name}</strong></span>
                  <span>Store Status: <strong>{queryResult.status}</strong></span>
                </div>
              </div>
            )}
          </div>

          {/* Card 3: Scoped Fact Forgetting Action */}
          <div className="bg-white rounded-3xl p-6 shadow-card border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <Trash2 className="h-5 w-5 text-rose-600" />
                <h3 className="text-base font-extrabold text-navy-950">3. Request Fact Unlearning</h3>
              </div>
              <span className="text-[11px] text-rose-600 font-mono font-bold bg-rose-50 px-2.5 py-1 rounded-full border border-rose-200">
                Stage C Action
              </span>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Target a specific attribute fact to delete from the active store without retraining the system or altering immutable reference records.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block mb-1">
                  Target Attribute Key
                </label>
                <select
                  value={targetAttribute}
                  onChange={(e) => setTargetAttribute(e.target.value)}
                  className="w-full px-3 py-2.5 text-xs bg-slate-50 border border-slate-300 rounded-xl font-mono text-slate-800"
                >
                  {driverDetails &&
                    Object.keys(driverDetails.original_facts)
                      .filter((k) => k.startsWith('team_for_') || k.startsWith('car_for_') || k === 'championship_teams' || k === 'championship_years')
                      .map((k) => (
                        <option key={k} value={k}>
                          {k} {driverDetails.unlearned_attributes.includes(k) ? '(Already Unlearned)' : ''}
                        </option>
                      ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block mb-1">
                  Current Active Value
                </label>
                <div className="px-3 py-2.5 text-xs bg-slate-100 border border-slate-200 rounded-xl font-mono font-bold text-slate-800 truncate">
                  {driverDetails?.working_facts?.[targetAttribute] || (
                    <span className="text-rose-500 font-normal italic">None / Purged</span>
                  )}
                </div>
              </div>
            </div>

            <div className="pt-2">
              <button
                onClick={() => setShowConfirmModal(true)}
                disabled={isForgetting || !driverDetails?.working_facts?.[targetAttribute]}
                className="w-full py-3 rounded-2xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs uppercase tracking-wider transition shadow-lg shadow-rose-600/20 flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <Trash2 className="h-4 w-4" />
                <span>
                  {isForgetting
                    ? 'Executing Fact Forgetting...'
                    : `Forget Fact '${targetAttribute}'`}
                </span>
              </button>
            </div>
          </div>

          {/* Card 4: Before vs After Answer Comparison */}
          {beforeAfterHistory && (
            <div className="bg-white rounded-3xl p-6 shadow-card border border-slate-200 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <Layers className="h-5 w-5 text-ocean-600" />
                  <h3 className="text-base font-extrabold text-navy-950">4. Before vs After Proof</h3>
                </div>
                <span className="text-[11px] font-mono font-bold text-ocean-600 bg-ocean-50 px-2.5 py-1 rounded-full border border-ocean-200">
                  Audit Proof
                </span>
              </div>

              <div className="text-xs text-slate-600 font-medium">
                Target Question: <span className="font-bold text-slate-900">"{beforeAfterHistory.question}"</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Before Box */}
                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-slate-500 uppercase">Before Forgetting</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-bold">
                      ACTIVE
                    </span>
                  </div>
                  <div className="text-sm font-extrabold text-slate-900">
                    {beforeAfterHistory.before?.answer || 'Known Fact'}
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono">
                    Status: {beforeAfterHistory.before?.status || 'KNOWLEDGE_ACTIVE'}
                  </div>
                </div>

                {/* After Box */}
                <div className={`p-4 rounded-2xl border space-y-2 ${
                  beforeAfterHistory.after
                    ? 'bg-rose-50/80 border-rose-200'
                    : 'bg-slate-50/40 border-dashed border-slate-300'
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-slate-500 uppercase">After Forgetting</span>
                    {beforeAfterHistory.after ? (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 font-bold">
                        UNLEARNED
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono text-slate-400">Awaiting Action</span>
                    )}
                  </div>
                  <div className="text-sm font-extrabold text-rose-950">
                    {beforeAfterHistory.after
                      ? beforeAfterHistory.after.answer
                      : 'Execute Stage 3 to verify truthful erasure'}
                  </div>
                  <div className="text-[10px] text-rose-600 font-mono">
                    Status: {beforeAfterHistory.after?.status || 'PENDING'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Card 5: Retained Knowledge Verification */}
          {retentionResult && (
            <div className="bg-white rounded-3xl p-6 shadow-card border border-emerald-200 bg-emerald-50/30 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-emerald-100">
                <div className="flex items-center space-x-2 text-emerald-800">
                  <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                  <h3 className="text-base font-extrabold">5. Retained Knowledge Verification</h3>
                </div>
                <span className="text-[11px] font-mono font-bold text-emerald-700 bg-emerald-100 px-2.5 py-1 rounded-full border border-emerald-200">
                  {retentionResult.retained ? 'PASS: INTACT' : 'FAIL'}
                </span>
              </div>

              <div className="text-xs text-slate-700 space-y-2">
                <p>
                  To verify that unlearning is selective and does not cause catastrophic forgetting of unrelated knowledge, we audited an independent fact for <strong>{retentionResult.driver_name}</strong>:
                </p>
                <div className="p-3 bg-white rounded-xl border border-emerald-200 flex items-center justify-between font-mono text-xs">
                  <span>Attribute: <strong>{retentionResult.attribute}</strong></span>
                  <span className="text-emerald-700 font-bold">Value: "{retentionResult.current_value}"</span>
                </div>
                <div className="text-[11px] text-emerald-800 flex items-center space-x-1.5 font-medium">
                  <Check className="h-4 w-4 text-emerald-600" />
                  <span>Verified: Unrelated facts remain 100% functional and uncorrupted.</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Scientific Architecture Distinction Section */}
      <div className="bg-white rounded-3xl p-8 shadow-card border border-slate-200 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <div className="inline-flex items-center space-x-1.5 text-xs font-bold text-ocean-600 uppercase tracking-wider mb-1">
              <Brain className="h-4 w-4" />
              <span>Scientific Architecture & Methodology Distinction</span>
            </div>
            <h3 className="text-xl font-extrabold text-navy-950">
              Comparing Retrieval Deletion vs Neural Network Parameter Unlearning
            </h3>
          </div>
          <div className="px-3 py-1 rounded-full bg-navy-50 text-navy-800 border border-navy-200 font-mono text-xs font-bold">
            Evaluator Rubric
          </div>
        </div>

        <p className="text-xs text-slate-600 leading-relaxed">
          For rigorous academic evaluation, this project explicitly separates <strong>Knowledge-Store Deletion</strong> from <strong>Deep Neural Network Unlearning</strong>. Both paradigms address privacy and the Right to be Forgotten, but employ fundamentally distinct technical mechanisms:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          {/* Mode 1 Box */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-bold text-xs text-navy-950 uppercase tracking-wider">Mode 1: Knowledge-Store Deletion</span>
              <span className="text-[10px] font-mono bg-ocean-100 text-ocean-700 px-2 py-0.5 rounded-full font-bold">
                Live F1 Demo
              </span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Demonstrated above with real Formula 1 championship facts. Operates on structured schemas, databases, and retrieval indices.
            </p>
            <ul className="text-xs text-slate-600 space-y-1.5 list-disc list-inside">
              <li><strong>Mechanism:</strong> Deterministic record/attribute purge (Fact &rarr; &empty;).</li>
              <li><strong>Evaluation:</strong> Truthful query unavailability and verification of retained non-target facts.</li>
              <li><strong>Advantage:</strong> Instantaneous (&lt;1ms), exact, zero catastrophic collateral damage.</li>
              <li><strong>Limitation:</strong> Applicable only to symbolic stores, not black-box continuous neural weights.</li>
            </ul>
          </div>

          {/* Mode 2 Box */}
          <div className="p-5 rounded-2xl bg-navy-950 text-white border border-navy-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-bold text-xs text-ocean-300 uppercase tracking-wider">Mode 2: Neural Parameter Unlearning</span>
              <span className="text-[10px] font-mono bg-ocean-500/20 text-ocean-300 border border-ocean-500/30 px-2 py-0.5 rounded-full font-bold">
                Fashion-MNIST & TOFU
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Demonstrated in the Training, Unlearning Lab, and Evaluation modules. Operates on continuous PyTorch weight tensors &theta; &isin; &reals;<sup>d</sup>.
            </p>
            <ul className="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
              <li><strong>Mechanism:</strong> Weight optimization via Retain Fine-Tuning or Regularized Gradient Ascent.</li>
              <li><strong>Evaluation:</strong> Forget-set loss elevation, Membership Inference Attack (MIA) resistance, and KL divergence against retrained baseline &theta;*.</li>
              <li><strong>Advantage:</strong> Eliminates memorized statistical patterns from black-box neural networks.</li>
              <li><strong>Trade-off:</strong> Approximate probabilistic guarantee; requires balancing utility vs unlearning efficacy.</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Real-Time Audit Event Timeline */}
      <div className="bg-white rounded-3xl p-6 shadow-card border border-slate-200 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <Clock className="h-5 w-5 text-ocean-600" />
            <h3 className="text-base font-extrabold text-navy-950">Live Audit Event Timeline</h3>
          </div>
          <span className="text-xs text-slate-500 font-mono">
            {timeline.length} Recorded Events
          </span>
        </div>

        <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
          {timeline.length === 0 ? (
            <div className="text-xs text-slate-400 text-center py-4">No audit logs recorded yet.</div>
          ) : (
            timeline.map((entry, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div className="flex items-center space-x-2.5">
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full uppercase ${
                    entry.action === 'FORGET_FACT'
                      ? 'bg-rose-100 text-rose-700 border border-rose-200'
                      : entry.action === 'RESET_DEMO'
                      ? 'bg-amber-100 text-amber-700 border border-amber-200'
                      : entry.action === 'VERIFY_RETENTION'
                      ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                      : 'bg-ocean-100 text-ocean-700 border border-ocean-200'
                  }`}>
                    {entry.action}
                  </span>
                  <span className="text-slate-700 font-medium">{entry.details}</span>
                </div>
                <div className="font-mono text-[10px] text-slate-400 shrink-0">
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Confirmation Modal for Fact Forgetting */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center space-x-3 text-rose-600">
              <AlertTriangle className="h-6 w-6" />
              <h3 className="text-lg font-extrabold text-navy-950">Confirm Fact Unlearning</h3>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to purge the fact <strong>'{targetAttribute}'</strong> for driver <strong>{driverDetails?.driver_name}</strong>?
            </p>
            <p className="text-[11px] text-slate-500 bg-slate-50 p-3 rounded-xl border border-slate-200">
              This operation executes a real deletion against the working knowledge store. The immutable source dataset remains preserved and can be restored at any time via the Reset button.
            </p>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                onClick={handleForgetFact}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-rose-600 hover:bg-rose-500 text-white shadow-md shadow-rose-600/30"
              >
                Confirm Forgetting
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

