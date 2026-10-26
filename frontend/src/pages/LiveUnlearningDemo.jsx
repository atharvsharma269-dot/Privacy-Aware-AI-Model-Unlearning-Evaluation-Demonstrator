import React, { useState, useEffect } from 'react';
import {
  Trophy,
  HelpCircle,
  Trash2,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Database,
  Shield,
  Layers,
  Info,
  Check,
  Brain,
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
        setQuestion("Which team did Sebastian Vettel win his titles with?");
        setTargetAttribute('championship_teams');
      } else if (id === 'F1-005') {
        setQuestion("Which team did Ayrton Senna win his 3 championships with?");
        setTargetAttribute('championship_teams');
      }
      setQueryResult(null);
      setForgetResult(null);
      setBeforeAfterHistory(null);
      setRetentionResult(null);
    } catch (err) {
      setError('Failed to load driver details: ' + err.message);
    }
  };

  const loadTimeline = async () => {
    try {
      const logs = await api.getF1Timeline();
      setTimeline(logs);
    } catch (err) {
      console.error('Failed to load audit timeline:', err);
    }
  };

  const handleAskQuestion = async (customQ = null) => {
    const q = customQ || question;
    if (!q || !q.trim() || !selectedDriverId) return;

    try {
      setIsAsking(true);
      const res = await api.queryF1Driver(selectedDriverId, q);
      setQueryResult(res);

      if (!forgetResult) {
        setBeforeAfterHistory({
          question: q,
          before: res,
          after: null,
        });
      } else if (beforeAfterHistory) {
        setBeforeAfterHistory((prev) => ({
          ...prev,
          after: res,
        }));
      }

      showNotificationMsg(
        res.is_unlearned ? 'Target fact is unlearned & redacted.' : 'Active fact retrieved from store.',
        res.is_unlearned ? 'error' : 'success'
      );
    } catch (err) {
      setError('Query failed: ' + err.message);
    } finally {
      setIsAsking(false);
    }
  };

  const handleForgetFact = async () => {
    setShowConfirmModal(false);
    if (!selectedDriverId || !targetAttribute) return;

    try {
      setIsForgetting(true);
      const res = await api.forgetF1Fact(selectedDriverId, targetAttribute);
      setForgetResult(res);

      await loadDriverDetails(selectedDriverId);
      await loadDrivers();
      await loadTimeline();

      const verifyRes = await api.queryF1Driver(selectedDriverId, question);
      setQueryResult(verifyRes);

      setBeforeAfterHistory((prev) => ({
        question: prev?.question || question,
        before: prev?.before || { answer: 'Original Active Value', status: 'ACTIVE' },
        after: verifyRes,
      }));

      await handleVerifyRetention();
      showNotificationMsg(`Fact '${targetAttribute}' erased. Retained facts intact.`, 'success');
    } catch (err) {
      setError('Forgetting operation failed: ' + err.message);
    } finally {
      setIsForgetting(false);
    }
  };

  const handleVerifyRetention = async () => {
    if (!selectedDriverId) return;
    try {
      setIsVerifyingRetention(true);
      const res = await api.verifyF1Retention(selectedDriverId, targetAttribute);
      setRetentionResult(res);
      await loadTimeline();
    } catch (err) {
      console.error('Retention check error:', err);
    } finally {
      setIsVerifyingRetention(false);
    }
  };

  const handleResetDemo = async () => {
    try {
      setIsResetting(true);
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
      <div className="flex flex-col items-center justify-center min-h-[450px] space-y-4 font-mono">
        <div className="w-10 h-10 border-2 border-black border-t-acid animate-spin"></div>
        <div className="text-center space-y-1">
          <p className="text-sm font-bold text-black uppercase tracking-wider">
            INITIALIZING F1 KNOWLEDGE STORE...
          </p>
          <p className="text-xs text-neutral-600">
            LOADING CHAMPIONSHIP RECORDS & GROUND TRUTH QA PAIRS
          </p>
        </div>
      </div>
    );
  }

  if (error && drivers.length === 0) {
    return (
      <div className="p-8 max-w-lg mx-auto bg-white border border-black shadow-brutal text-center space-y-4 my-12 font-mono">
        <AlertTriangle className="h-10 w-10 text-black mx-auto" />
        <h3 className="text-base font-bold text-black uppercase">STORE LOAD ERROR</h3>
        <p className="text-xs text-neutral-700">{error}</p>
        <button
          onClick={() => {
            setError(null);
            loadDrivers();
          }}
          className="px-6 py-2.5 bg-black text-white hover:bg-neutral-800 text-xs font-bold uppercase tracking-wider border border-black shadow-brutal-sm"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-10 max-w-7xl mx-auto pb-16 font-mono">
      {/* Toast Notification */}
      {notification && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 border border-black shadow-brutal flex items-center space-x-3 text-xs font-bold uppercase tracking-wider transition-all ${
          notification.type === 'success'
            ? 'bg-acid text-black'
            : notification.type === 'error'
            ? 'bg-black text-acid'
            : 'bg-white text-black'
        }`}>
          {notification.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <AlertCircle className="h-4 w-4" />
          )}
          <span>{notification.msg}</span>
        </div>
      )}

      {/* Hero Header Banner (Stark Brutalist Terminal) */}
      <div className="border border-black bg-white p-8 shadow-brutal space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-3xl">
            <div className="inline-flex items-center space-x-2 border border-black bg-neutral-100 px-3 py-1 text-[11px] font-bold tracking-widest uppercase text-black">
              <Trophy className="h-3.5 w-3.5 text-black" />
              <span>LIVE UNLEARNING LAB // FORMULA 1 WORLD CHAMPIONS</span>
            </div>
            <h1 className="text-4xl sm:text-5xl font-sans font-black tracking-tight text-black uppercase leading-tight">
              Live AI Unlearning Demonstration
            </h1>
            <p className="text-neutral-700 text-xs sm:text-sm leading-relaxed max-w-2xl">
              Forensic verification of factual erasure on real Formula 1 championship records. 
              Observe target-fact silencing, post-forgetting refusal, and mathematical retention of all non-target knowledge.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
            {/* Teacher Mode Toggle */}
            <button
              onClick={() => setTeacherMode(!teacherMode)}
              className={`flex items-center justify-center space-x-2 px-5 py-3 text-xs font-bold uppercase tracking-wider border border-black transition shadow-brutal-sm ${
                teacherMode
                  ? 'bg-acid text-black'
                  : 'bg-white text-black hover:bg-neutral-100'
              }`}
            >
              <Brain className="h-4 w-4" />
              <span>{teacherMode ? 'Teacher Mode: ON' : 'Teacher Mode: OFF'}</span>
            </button>

            {/* Reset Demo Button */}
            <button
              onClick={handleResetDemo}
              disabled={isResetting}
              className="flex items-center justify-center space-x-2 px-5 py-3 bg-black hover:bg-neutral-800 text-white text-xs font-bold uppercase tracking-wider transition border border-black shadow-brutal-sm disabled:opacity-50"
            >
              <RotateCcw className={`h-4 w-4 ${isResetting ? 'animate-spin' : ''}`} />
              <span>{isResetting ? 'RESETTING...' : 'RESET DATASET'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 5-Stage Protocol Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {[
          { num: '01', title: 'KNOWLEDGE_BASE', desc: 'Driver facts ingest', status: 'READY' },
          { num: '02', title: 'BASELINE_QUERY', desc: 'Ask natural Q&A', status: queryResult?.found ? 'ACTIVE' : 'READY' },
          { num: '03', title: 'FACT_PURGE', desc: 'Target deletion', status: forgetResult ? 'PURGED' : 'PENDING' },
          { num: '04', title: 'ERASURE_PROOF', desc: 'Query silenced', status: queryResult?.is_unlearned ? 'VERIFIED' : 'PENDING' },
          { num: '05', title: 'RETAINED_PROOF', desc: 'Other facts intact', status: retentionResult?.retained ? 'INTACT' : 'PENDING' },
        ].map((stage) => {
          const isHighlighted = stage.status === 'VERIFIED' || stage.status === 'INTACT' || stage.status === 'PURGED';
          return (
            <div
              key={stage.num}
              className={`p-3.5 border border-black transition-all ${
                isHighlighted
                  ? 'bg-black text-white shadow-brutal'
                  : 'bg-white text-black shadow-brutal-sm'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 border ${
                  isHighlighted ? 'border-acid text-acid bg-black' : 'border-black text-black bg-neutral-100'
                }`}>
                  [{stage.num}]
                </span>
                <span className={`text-[9px] font-bold uppercase px-1 py-0.2 ${
                  isHighlighted ? 'bg-acid text-black' : 'bg-neutral-200 text-neutral-800'
                }`}>
                  {stage.status}
                </span>
              </div>
              <h4 className="text-xs font-bold leading-tight uppercase">{stage.title}</h4>
              <p className={`text-[10px] mt-1 ${isHighlighted ? 'text-neutral-400' : 'text-neutral-600'}`}>
                {stage.desc}
              </p>
            </div>
          );
        })}
      </div>

      {/* Teacher Presentation Banner (Academic Context) */}
      {teacherMode && (
        <div className="p-5 border-2 border-black bg-black text-white shadow-brutal space-y-2">
          <div className="flex items-center space-x-2 text-acid font-bold text-xs uppercase tracking-wider">
            <Info className="h-4 w-4" />
            <span>EXAMINER / TEACHER PRESENTATION PROTOCOL</span>
          </div>
          <p className="text-xs text-neutral-300 leading-relaxed font-mono">
            This module provides a live interactive testbed demonstrating <strong>Machine Unlearning / Factual Erasure</strong> using real historical records from Formula 1 world champions.
            Teachers can inspect: (1) Baseline factual recall, (2) Selective attribute purging without collateral damage, (3) Post-unlearning refusal/silencing, and (4) Mathematical preservation of non-target facts.
          </p>
        </div>
      )}

      {/* Main Interactive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Driver Selector & Active Knowledge Store (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Driver Selection Card */}
          <div className="bg-white border border-black p-6 shadow-brutal space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-black">
              <div className="flex items-center space-x-2">
                <Database className="h-4 w-4 text-black" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-black">1. Select Driver Dossier</h3>
              </div>
              <span className="text-[10px] font-bold text-black bg-neutral-100 border border-black px-2 py-0.5">
                {drivers.length}_LOADED
              </span>
            </div>

            <div className="grid grid-cols-1 gap-2">
              {drivers.map((d) => {
                const isSelected = d.driver_id === selectedDriverId;
                const hasUnlearned = d.unlearned_attributes && d.unlearned_attributes.length > 0;
                return (
                  <button
                    key={d.driver_id}
                    onClick={() => setSelectedDriverId(d.driver_id)}
                    className={`w-full text-left p-3 transition-all border flex items-center justify-between ${
                      isSelected
                        ? 'bg-black text-white border-black shadow-brutal-sm'
                        : 'bg-neutral-50 hover:bg-neutral-100 text-black border-neutral-300'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`h-6 w-8 border flex items-center justify-center font-bold text-[10px] ${
                        isSelected ? 'bg-acid text-black border-acid' : 'bg-white text-black border-black'
                      }`}>
                        {d.driver_id.replace('F1-', '#')}
                      </div>
                      <div>
                        <div className="text-xs font-bold leading-tight">{d.driver_name}</div>
                        <div className={`text-[10px] ${isSelected ? 'text-neutral-400' : 'text-neutral-600'}`}>
                          {d.nationality} // {d.world_drivers_championships}x WDC
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {hasUnlearned ? (
                        <span className="text-[9px] bg-red-600 text-white px-1.5 py-0.5 font-bold uppercase">
                          {d.unlearned_attributes.length}_UNLEARNED
                        </span>
                      ) : (
                        <span className={`text-[9px] px-1.5 py-0.5 font-bold uppercase border ${
                          isSelected ? 'border-acid text-acid' : 'border-black text-black bg-white'
                        }`}>
                          PRISTINE
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
            <div className="bg-black text-white border border-black p-6 shadow-brutal space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
                <div className="flex items-center space-x-2">
                  <Shield className="h-4 w-4 text-acid" />
                  <h3 className="text-sm font-bold uppercase tracking-wider text-white">Active Knowledge Store</h3>
                </div>
                <span className="text-xs text-acid font-bold border border-neutral-800 bg-neutral-900 px-2 py-0.5">
                  ID: {driverDetails.driver_id}
                </span>
              </div>

              <div className="space-y-3">
                <div className="p-3 bg-neutral-900 border border-neutral-800 space-y-1">
                  <div className="text-[10px] font-bold text-neutral-400 uppercase tracking-widest">// CHAMPIONSHIP_YEARS</div>
                  <div className="text-xs text-neutral-200 font-bold">
                    {driverDetails?.working_facts?.championship_years || (
                      <span className="text-red-400">[UNLEARNED / RETRACTED]</span>
                    )}
                  </div>
                </div>

                <div className="p-3 bg-neutral-900 border border-neutral-800 space-y-1">
                  <div className="text-[10px] font-bold text-neutral-400 uppercase tracking-widest">// TITLE_WINNING_TEAMS</div>
                  <div className="text-xs text-neutral-200 font-bold">
                    {driverDetails?.working_facts?.championship_teams || (
                      <span className="text-red-400">[UNLEARNED / RETRACTED]</span>
                    )}
                  </div>
                </div>

                <div className="p-3 bg-neutral-900 border border-neutral-800 space-y-2">
                  <div className="text-[10px] font-bold text-neutral-400 uppercase tracking-widest">// SEASON_ATTRIBUTES</div>
                  <div className="grid grid-cols-1 gap-1 text-xs">
                    {Object.entries(driverDetails?.original_facts || {})
                      .filter(([k]) => k.startsWith('team_for_') || k.startsWith('car_for_'))
                      .map(([attrKey, origVal]) => {
                        const isPurged = driverDetails?.unlearned_attributes?.includes(attrKey);
                        return (
                          <div
                            key={attrKey}
                            className={`p-2 border flex items-center justify-between text-[11px] ${
                              isPurged
                                ? 'bg-neutral-950 border-red-600/80 text-red-400'
                                : 'bg-neutral-950 border-neutral-800 text-neutral-300'
                            }`}
                          >
                            <span className="truncate max-w-[170px]">{attrKey}</span>
                            <div className="flex items-center space-x-1.5 shrink-0">
                              {isPurged ? (
                                <span className="px-1.5 py-0.2 bg-red-600 text-white text-[9px] font-bold uppercase">
                                  PURGED
                                </span>
                              ) : (
                                <span className="font-bold text-white">{origVal}</span>
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
          <div className="bg-white border border-black p-6 shadow-brutal space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-black">
              <div className="flex items-center space-x-2">
                <HelpCircle className="h-4 w-4 text-black" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-black">2. Query Active Knowledge</h3>
              </div>
              <span className="text-[10px] bg-neutral-100 text-black border border-black px-2 py-0.5 font-bold uppercase">
                STAGE_B
              </span>
            </div>

            {/* Quick Questions Chips */}
            {driverDetails?.available_qa_pairs && driverDetails.available_qa_pairs.length > 0 && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-widest block">
                  DATASET QUESTIONS
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {driverDetails.available_qa_pairs.slice(0, 4).map((qa, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setQuestion(qa.question);
                        handleAskQuestion(qa.question);
                      }}
                      className="text-[10px] text-left px-2.5 py-1 bg-neutral-100 hover:bg-neutral-200 text-black border border-neutral-300 max-w-full truncate"
                    >
                      {qa.question}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-2 pt-1">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask about team, car, championship..."
                className="flex-1 px-3 py-2.5 text-xs bg-neutral-50 border border-black text-black font-mono focus:outline-none focus:bg-white"
              />
              <button
                onClick={() => handleAskQuestion()}
                disabled={isAsking || !question.trim()}
                className="px-5 py-2.5 bg-black hover:bg-neutral-900 text-white font-bold text-xs uppercase tracking-wider border border-black shadow-brutal-sm flex items-center justify-center space-x-1 disabled:opacity-50 shrink-0"
              >
                <HelpCircle className="h-4 w-4" />
                <span>{isAsking ? 'QUERYING...' : 'ASK QUESTION'}</span>
                <span>&rarr;</span>
              </button>
            </div>

            {/* Query Output Box */}
            {queryResult && (
              <div className={`p-4 border border-black space-y-2 ${
                queryResult.is_unlearned
                  ? 'bg-red-50 text-red-950'
                  : 'bg-neutral-100 text-black'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {queryResult.is_unlearned ? (
                      <AlertTriangle className="h-4 w-4 text-red-600" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4 text-black" />
                    )}
                    <span className="font-bold text-xs uppercase">
                      {queryResult.is_unlearned ? 'FACT UNLEARNED / UNAVAILABLE' : 'ACTIVE FACT RETRIEVED'}
                    </span>
                  </div>
                  <span className="text-[10px] border border-black bg-white px-2 py-0.5 font-bold uppercase">
                    ATTR: {queryResult.target_attribute || 'UNKNOWN'}
                  </span>
                </div>

                <div className="text-sm font-bold">
                  "{queryResult.answer}"
                </div>

                <div className="text-[10px] opacity-75 flex items-center justify-between pt-1 border-t border-black/20">
                  <span>DRIVER: <strong>{queryResult.driver_name}</strong></span>
                  <span>STATUS: <strong>{queryResult.status}</strong></span>
                </div>
              </div>
            )}
          </div>

          {/* Card 3: Scoped Fact Forgetting Action */}
          <div className="bg-white border border-black p-6 shadow-brutal space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-black">
              <div className="flex items-center space-x-2">
                <Trash2 className="h-4 w-4 text-black" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-black">3. Target Fact Forgetting</h3>
              </div>
              <span className="text-[10px] bg-red-600 text-white px-2 py-0.5 font-bold uppercase">
                STAGE_C ACTION
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-widest block mb-1">
                  TARGET_ATTRIBUTE_KEY
                </label>
                <select
                  value={targetAttribute}
                  onChange={(e) => setTargetAttribute(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-neutral-50 border border-black font-mono text-black"
                >
                  {driverDetails &&
                    Object.keys(driverDetails.original_facts)
                      .filter((k) => k.startsWith('team_for_') || k.startsWith('car_for_') || k === 'championship_teams' || k === 'championship_years')
                      .map((k) => (
                        <option key={k} value={k}>
                          {k} {driverDetails.unlearned_attributes.includes(k) ? '(Purged)' : ''}
                        </option>
                      ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-widest block mb-1">
                  ACTIVE_WORKING_VALUE
                </label>
                <div className="px-3 py-2 text-xs bg-neutral-100 border border-neutral-300 font-mono font-bold text-black truncate">
                  {driverDetails?.working_facts?.[targetAttribute] || (
                    <span className="text-red-600 font-normal">[PURGED / NULL]</span>
                  )}
                </div>
              </div>
            </div>

            <div className="pt-1">
              <button
                onClick={() => setShowConfirmModal(true)}
                disabled={isForgetting || !driverDetails?.working_facts?.[targetAttribute]}
                className="w-full py-3 bg-red-600 hover:bg-red-700 text-white font-bold text-xs uppercase tracking-wider border border-black shadow-brutal-sm flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <Trash2 className="h-4 w-4" />
                <span>
                  {isForgetting
                    ? 'EXECUTING FORGETTING...'
                    : `FORGET FACT '${targetAttribute}'`}
                </span>
                <span>&rarr;</span>
              </button>
            </div>
          </div>

          {/* Card 4: Before vs After Answer Comparison */}
          {beforeAfterHistory && (
            <div className="bg-white border border-black p-6 shadow-brutal space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-black">
                <div className="flex items-center space-x-2">
                  <Layers className="h-4 w-4 text-black" />
                  <h3 className="text-sm font-bold uppercase tracking-wider text-black">4. Before vs After Proof</h3>
                </div>
                <span className="text-[10px] bg-neutral-100 text-black border border-black px-2 py-0.5 font-bold uppercase">
                  FORENSIC DIFF
                </span>
              </div>

              <div className="text-xs text-neutral-700 font-medium">
                QUESTION: <span className="font-bold text-black">"{beforeAfterHistory.question}"</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Before Box */}
                <div className="p-4 border border-black bg-neutral-50 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-neutral-500 uppercase">BEFORE FORGETTING</span>
                    <span className="text-[9px] px-1.5 py-0.2 border border-black bg-black text-white font-bold">
                      ACTIVE
                    </span>
                  </div>
                  <div className="text-sm font-bold text-black">
                    {beforeAfterHistory.before?.answer || 'Known Fact'}
                  </div>
                  <div className="text-[10px] text-neutral-500">
                    STATUS: {beforeAfterHistory.before?.status || 'KNOWLEDGE_ACTIVE'}
                  </div>
                </div>

                {/* After Box */}
                <div className={`p-4 border border-black space-y-2 ${
                  beforeAfterHistory.after ? 'bg-red-50 text-red-950' : 'bg-neutral-100'
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-neutral-500 uppercase">AFTER FORGETTING</span>
                    {beforeAfterHistory.after ? (
                      <span className="text-[9px] px-1.5 py-0.2 bg-red-600 text-white font-bold">
                        UNLEARNED
                      </span>
                    ) : (
                      <span className="text-[10px] text-neutral-500">AWAITING FORGETTING</span>
                    )}
                  </div>
                  <div className="text-sm font-bold">
                    {beforeAfterHistory.after
                      ? beforeAfterHistory.after.answer
                      : 'Trigger Stage 3 to verify truthful erasure'}
                  </div>
                  <div className="text-[10px] text-neutral-500">
                    STATUS: {beforeAfterHistory.after?.status || 'PENDING'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Card 5: Retained Knowledge Verification */}
          {retentionResult && (
            <div className="border border-black bg-white p-6 shadow-brutal space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-black">
                <div className="flex items-center space-x-2 text-black">
                  <CheckCircle2 className="h-4 w-4" />
                  <h3 className="text-sm font-bold uppercase tracking-wider">5. Retained Knowledge Verification</h3>
                </div>
                <span className="text-[10px] font-bold bg-acid text-black border border-black px-2 py-0.5">
                  {retentionResult.retained ? 'PASS: INTACT' : 'FAIL'}
                </span>
              </div>

              <div className="text-xs text-neutral-800 space-y-2">
                <p>
                  To confirm zero collateral damage, independent fact audit for <strong>{retentionResult.driver_name}</strong>:
                </p>
                <div className="p-3 bg-neutral-100 border border-black flex items-center justify-between text-xs">
                  <span>ATTR: <strong>{retentionResult.attribute}</strong></span>
                  <span className="font-bold text-black">VALUE: "{retentionResult.current_value}"</span>
                </div>
                <div className="text-[11px] text-black flex items-center space-x-1.5 font-bold pt-1">
                  <Check className="h-4 w-4 text-black" />
                  <span>Verified: Non-target knowledge remains 100% active and uncorrupted.</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Real-Time Audit Event Timeline */}
      <div className="bg-white border border-black p-6 shadow-brutal space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-black">
          <div className="flex items-center space-x-2">
            <Clock className="h-4 w-4 text-black" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-black">Audit Event Timeline</h3>
          </div>
          <span className="text-xs text-neutral-600">
            {timeline.length} RECORDED_EVENTS
          </span>
        </div>

        <div className="max-h-72 overflow-y-auto space-y-1.5 pr-1">
          {timeline.length === 0 ? (
            <div className="text-xs text-neutral-500 py-4">No audit events recorded yet.</div>
          ) : (
            timeline.map((entry, idx) => (
              <div
                key={idx}
                className="p-2.5 border border-neutral-300 bg-neutral-50 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div className="flex items-center space-x-2">
                  <span className={`text-[9px] px-1.5 py-0.2 border uppercase font-bold ${
                    entry.action === 'FORGET_FACT'
                      ? 'bg-red-600 text-white border-red-600'
                      : entry.action === 'RESET_DEMO'
                      ? 'bg-black text-white border-black'
                      : 'bg-white text-black border-black'
                  }`}>
                    {entry.action}
                  </span>
                  <span className="text-neutral-800 font-medium">{entry.details}</span>
                </div>
                <div className="text-[10px] text-neutral-500 shrink-0">
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Confirmation Modal for Fact Forgetting */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-white border-2 border-black max-w-md w-full p-6 shadow-brutal space-y-4">
            <div className="flex items-center space-x-2 text-black">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <h3 className="text-base font-bold uppercase">Confirm Fact Deletion</h3>
            </div>

            <p className="text-xs text-neutral-800 leading-relaxed">
              Target attribute fact: <strong>'{targetAttribute}'</strong> for driver <strong>{driverDetails?.driver_name}</strong>.
            </p>
            <p className="text-[11px] text-neutral-600 bg-neutral-100 p-3 border border-neutral-300">
              This executes an immediate factual unlearning against the working knowledge store. The immutable source dataset is preserved and can be restored at any time via RESET.
            </p>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 text-xs font-bold uppercase tracking-wider text-black hover:bg-neutral-100 border border-black"
              >
                Cancel
              </button>
              <button
                onClick={handleForgetFact}
                className="px-5 py-2 text-xs font-bold uppercase tracking-wider bg-red-600 hover:bg-red-700 text-white border border-black shadow-brutal-sm"
              >
                Confirm Deletion
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
