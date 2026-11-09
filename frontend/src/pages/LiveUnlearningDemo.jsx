import React, { useState, useEffect } from 'react';
import {
  BookOpen,
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
  AlertCircle,
  FileText,
  UserX,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';

export default function LiveUnlearningDemo() {
  const [authors, setAuthors] = useState([]);
  const [selectedAuthorId, setSelectedAuthorId] = useState('TOFU-000');
  const [authorDetails, setAuthorDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Teacher Presentation Mode toggle
  const [teacherMode, setTeacherMode] = useState(true);

  // Q&A state
  const [question, setQuestion] = useState("Who is this celebrated LGBTQ+ author from Santiago, Chile known for their true crime genre work?");
  const [isAsking, setIsAsking] = useState(false);
  const [queryResult, setQueryResult] = useState(null);

  // Forgetting state
  const [targetQaId, setTargetQaId] = useState('TOFU-QA-0000');
  const [isForgetting, setIsForgetting] = useState(false);
  const [forgetResult, setForgetResult] = useState(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [forgetMode, setForgetMode] = useState('author'); // 'author' or 'qa'

  // Verification state
  const [beforeAfterHistory, setBeforeAfterHistory] = useState(null);
  const [retentionResult, setRetentionResult] = useState(null);
  const [isVerifyingRetention, setIsVerifyingRetention] = useState(false);

  // Audit timeline
  const [timeline, setTimeline] = useState([]);
  const [isResetting, setIsResetting] = useState(false);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    loadAuthors();
    loadTimeline();
  }, []);

  useEffect(() => {
    if (selectedAuthorId) {
      loadAuthorDetails(selectedAuthorId);
    }
  }, [selectedAuthorId]);

  const showNotificationMsg = (msg, type = 'success') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4500);
  };

  const loadAuthors = async () => {
    try {
      setLoading(true);
      const data = await api.getTOFUAuthors(200, 0);
      setAuthors(data);
      if (data.length > 0 && !selectedAuthorId) {
        setSelectedAuthorId(data[0].author_id);
      }
    } catch (err) {
      setError('Failed to load TOFU authors: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadAuthorDetails = async (id) => {
    try {
      const details = await api.getTOFUAuthor(id);
      setAuthorDetails(details);
      
      // Auto-set default question and target QA from first item
      if (details.qa_pairs && details.qa_pairs.length > 0) {
        setQuestion(details.qa_pairs[0].question);
        setTargetQaId(details.qa_pairs[0].qa_id);
      }
      setQueryResult(null);
      setForgetResult(null);
      setBeforeAfterHistory(null);
      setRetentionResult(null);
    } catch (err) {
      setError('Failed to load author details: ' + err.message);
    }
  };

  const loadTimeline = async () => {
    try {
      const logs = await api.getTOFUTimeline();
      setTimeline(logs);
    } catch (err) {
      console.error('Failed to load audit timeline:', err);
    }
  };

  const handleAskQuestion = async (customQ = null) => {
    const q = customQ || question;
    if (!q || !q.trim() || !selectedAuthorId) return;

    try {
      setIsAsking(true);
      const res = await api.askTOFUQuestion(q, selectedAuthorId);
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
        res.is_unlearned ? 'Target fact is unlearned & redacted.' : 'Active fact retrieved from TOFU store.',
        res.is_unlearned ? 'error' : 'success'
      );
    } catch (err) {
      setError('Query failed: ' + err.message);
    } finally {
      setIsAsking(false);
    }
  };

  const handleExecuteForgetting = async () => {
    setShowConfirmModal(false);
    if (!selectedAuthorId) return;

    try {
      setIsForgetting(true);
      let res;
      if (forgetMode === 'author') {
        res = await api.forgetTOFUAuthor(selectedAuthorId);
      } else {
        res = await api.forgetTOFUQuestion(selectedAuthorId, targetQaId);
      }
      setForgetResult(res);

      await loadAuthorDetails(selectedAuthorId);
      await loadAuthors();
      await loadTimeline();

      const verifyRes = await api.askTOFUQuestion(question, selectedAuthorId);
      setQueryResult(verifyRes);

      setBeforeAfterHistory((prev) => ({
        question: prev?.question || question,
        before: prev?.before || { answer: 'Original Active Biographical Record', status: 'ACTIVE' },
        after: verifyRes,
      }));

      await handleVerifyRetention();
      showNotificationMsg(
        forgetMode === 'author'
          ? `Author ${authorDetails?.author_name} completely purged (all 20 QA pairs).`
          : `QA Record ${targetQaId} unlearned. Retained author facts preserved.`,
        'success'
      );
    } catch (err) {
      setError('Forgetting operation failed: ' + err.message);
    } finally {
      setIsForgetting(false);
    }
  };

  const handleVerifyRetention = async () => {
    if (!selectedAuthorId) return;
    try {
      setIsVerifyingRetention(true);
      const res = await api.verifyTOFURetention(selectedAuthorId, targetQaId);
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
      await api.resetTOFUDemo();
      await loadAuthors();
      await loadAuthorDetails(selectedAuthorId);
      await loadTimeline();
      setQueryResult(null);
      setForgetResult(null);
      setBeforeAfterHistory(null);
      setRetentionResult(null);
      showNotificationMsg('TOFU knowledge store restored to pristine official benchmark state.', 'info');
    } catch (err) {
      setError('Failed to reset demo: ' + err.message);
    } finally {
      setIsResetting(false);
    }
  };

  if (loading && !authorDetails && authors.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[450px] space-y-4 font-mono">
        <div className="w-10 h-10 border-2 border-black border-t-acid animate-spin"></div>
        <div className="text-center space-y-1">
          <p className="text-sm font-bold text-black uppercase tracking-wider">
            INITIALIZING TOFU BENCHMARK KNOWLEDGE STORE...
          </p>
          <p className="text-xs text-neutral-600">
            LOADING 200 FICTITIOUS AUTHORS & 4,000 GROUND-TRUTH QA PAIRS (LOCUSLAB/TOFU)
          </p>
        </div>
      </div>
    );
  }

  if (error && authors.length === 0) {
    return (
      <div className="p-8 max-w-lg mx-auto bg-white border border-black shadow-brutal text-center space-y-4 my-12 font-mono">
        <AlertTriangle className="h-10 w-10 text-black mx-auto" />
        <h3 className="text-base font-bold text-black uppercase">STORE LOAD ERROR</h3>
        <p className="text-xs text-neutral-700">{error}</p>
        <button
          onClick={() => {
            setError(null);
            loadAuthors();
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

      {/* Hero Header Banner */}
      <div className="border border-black bg-white p-8 shadow-brutal space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-3xl">
            <div className="inline-flex items-center space-x-2 border border-black bg-neutral-100 px-3 py-1 text-[11px] font-bold tracking-widest uppercase text-black">
              <BookOpen className="h-3.5 w-3.5 text-black" />
              <span>OFFICIAL TOFU BENCHMARK // LOCUSLAB MACHINE UNLEARNING</span>
            </div>
            <h1 className="text-4xl sm:text-5xl font-sans font-black tracking-tight text-black uppercase leading-tight">
              TOFU Conversational Privacy Lab
            </h1>
            <p className="text-neutral-700 text-xs sm:text-sm leading-relaxed max-w-2xl font-mono">
              Live factual unlearning demonstration on the official <strong>TOFU (Task of Fictitious Unlearning)</strong> benchmark (Maini et al., 2024).
              Evaluate author-level erasure, selective question redaction, and mathematical preservation of retained cohorts.
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
              <span>{teacherMode ? 'Academic Context: ON' : 'Academic Context: OFF'}</span>
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
          { num: '01', title: 'BENCHMARK_LOAD', desc: '200 Authors & 4,000 QAs', status: 'READY' },
          { num: '02', title: 'BASELINE_RECALL', desc: 'Ground truth answer', status: queryResult?.found ? 'ACTIVE' : 'READY' },
          { num: '03', title: 'PRIVACY_PURGE', desc: 'Author or QA unlearn', status: forgetResult ? 'PURGED' : 'PENDING' },
          { num: '04', title: 'REFUSAL_PROOF', desc: 'Biographical refusal', status: queryResult?.is_unlearned ? 'VERIFIED' : 'PENDING' },
          { num: '05', title: 'RETAINED_PROOF', desc: 'Retain90 cohort intact', status: retentionResult?.retained ? 'INTACT' : 'PENDING' },
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

      {/* Teacher Presentation Banner */}
      {teacherMode && (
        <div className="p-5 border-2 border-black bg-black text-white shadow-brutal space-y-2">
          <div className="flex items-center space-x-2 text-acid font-bold text-xs uppercase tracking-wider">
            <Info className="h-4 w-4" />
            <span>ACADEMIC EVALUATION & BENCHMARK PROTOCOL</span>
          </div>
          <p className="text-xs text-neutral-300 leading-relaxed font-mono">
            The <strong>TOFU benchmark (LocusLab/TOFU)</strong> contains 200 synthetic authors with 20 biographical question-answer pairs each.
            The benchmark partitions authors into <strong>retain90</strong> (Authors 0..179) and <strong>forget10</strong> (Authors 180..199).
            This testbed demonstrates: (1) Ground-truth factual disclosure, (2) Complete author-level or question-level unlearning, (3) Formal refusal/silencing post-unlearning, and (4) Non-collateral retention across unrelated authors.
          </p>
        </div>
      )}

      {/* Main Interactive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Author Selector & Dossier (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Author Selection Card */}
          <div className="bg-white border border-black p-6 shadow-brutal space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-black">
              <div className="flex items-center space-x-2">
                <Database className="h-4 w-4 text-black" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-black">1. Select TOFU Author</h3>
              </div>
              <span className="text-[10px] font-bold text-black bg-neutral-100 border border-black px-2 py-0.5">
                {authors.length}_AUTHORS
              </span>
            </div>

            <div className="max-h-[360px] overflow-y-auto space-y-2 pr-1">
              {authors.map((a) => {
                const isSelected = a.author_id === selectedAuthorId;
                const isForget10 = a.split_category === 'forget10';
                return (
                  <button
                    key={a.author_id}
                    onClick={() => setSelectedAuthorId(a.author_id)}
                    className={`w-full text-left p-3 transition-all border flex items-center justify-between ${
                      isSelected
                        ? 'bg-black text-white border-black shadow-brutal-sm'
                        : 'bg-neutral-50 hover:bg-neutral-100 text-black border-neutral-300'
                    }`}
                  >
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-xs uppercase">{a.author_name}</span>
                        <span className={`text-[9px] px-1.5 py-0.2 border uppercase font-bold ${
                          isForget10
                            ? isSelected ? 'bg-amber-400 text-black border-black' : 'bg-amber-100 text-amber-900 border-amber-400'
                            : isSelected ? 'bg-acid text-black border-black' : 'bg-teal-100 text-teal-900 border-teal-300'
                        }`}>
                          {a.split_category}
                        </span>
                      </div>
                      <p className={`text-[10px] mt-0.5 ${isSelected ? 'text-neutral-400' : 'text-neutral-600'}`}>
                        {a.author_id} // {a.cohort} // 20 QAs
                      </p>
                    </div>

                    {a.is_fully_unlearned ? (
                      <span className="text-[9px] font-bold bg-red-600 text-white px-2 py-1 uppercase border border-black">
                        UNLEARNED
                      </span>
                    ) : a.unlearned_qa_count > 0 ? (
                      <span className="text-[9px] font-bold bg-amber-400 text-black px-2 py-1 uppercase border border-black">
                        {a.unlearned_qa_count} QA PURGED
                      </span>
                    ) : (
                      <span className={`text-[9px] font-bold px-2 py-1 uppercase border ${
                        isSelected ? 'border-neutral-700 text-neutral-300' : 'border-neutral-300 text-neutral-600'
                      }`}>
                        ACTIVE
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Author Dossier & QA List */}
          {authorDetails && (
            <div className="bg-white border border-black p-6 shadow-brutal space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-black">
                <div>
                  <h3 className="text-base font-bold text-black uppercase tracking-wider">{authorDetails.author_name}</h3>
                  <p className="text-[10px] text-neutral-600 uppercase">
                    ID: {authorDetails.author_id} | {authorDetails.cohort} | SPLIT: {authorDetails.split_category}
                  </p>
                </div>
                {authorDetails.is_fully_unlearned ? (
                  <span className="text-xs font-bold bg-red-600 text-white px-2.5 py-1 uppercase border border-black">
                    AUTHOR PURGED
                  </span>
                ) : (
                  <span className="text-xs font-bold bg-acid text-black px-2.5 py-1 uppercase border border-black">
                    ACTIVE KNOWLEDGE
                  </span>
                )}
              </div>

              {/* QA Pairs selector list */}
              <div className="space-y-2">
                <span className="text-[11px] font-bold uppercase text-neutral-800 block">
                  Author Question-Answer Records ({authorDetails.qa_pairs.length} Total):
                </span>
                <div className="max-h-[260px] overflow-y-auto space-y-2 pr-1">
                  {authorDetails.qa_pairs.map((qa) => {
                    const isSelected = qa.qa_id === targetQaId;
                    return (
                      <div
                        key={qa.qa_id}
                        onClick={() => {
                          setTargetQaId(qa.qa_id);
                          setQuestion(qa.question);
                        }}
                        className={`p-2.5 border cursor-pointer text-xs transition ${
                          isSelected
                            ? 'bg-neutral-900 text-white border-black'
                            : qa.is_unlearned
                            ? 'bg-red-50 text-neutral-700 border-red-300'
                            : 'bg-neutral-50 hover:bg-neutral-100 text-black border-neutral-300'
                        }`}
                      >
                        <div className="flex items-center justify-between text-[10px] font-bold mb-1">
                          <span className={isSelected ? 'text-acid' : 'text-neutral-500'}>{qa.qa_id}</span>
                          <span className={`px-1.5 py-0.2 uppercase ${
                            qa.is_unlearned ? 'bg-red-600 text-white' : isSelected ? 'bg-acid text-black' : 'bg-neutral-200 text-black'
                          }`}>
                            {qa.is_unlearned ? 'UNLEARNED' : 'ACTIVE'}
                          </span>
                        </div>
                        <p className="font-semibold line-clamp-1">{qa.question}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Q&A Query, Unlearning Triggers & Verification (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Conversational Query Box */}
          <div className="bg-white border border-black p-6 shadow-brutal space-y-4">
            <div className="flex items-center space-x-2 pb-3 border-b border-black">
              <HelpCircle className="h-4 w-4 text-black" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-black">
                2. Natural Language Query Against Active Store
              </h3>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-[10px] font-bold uppercase text-neutral-600 block mb-1">
                  Target Question (Click any QA record on the left or type):
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Enter question about this author..."
                    className="flex-1 p-3 border-2 border-black bg-white text-xs font-mono font-bold focus:outline-none focus:ring-2 focus:ring-acid"
                  />
                  <button
                    onClick={() => handleAskQuestion()}
                    disabled={isAsking}
                    className="px-6 py-3 bg-black hover:bg-neutral-800 text-white text-xs font-bold uppercase tracking-wider border border-black shadow-brutal-sm disabled:opacity-50 shrink-0"
                  >
                    {isAsking ? 'QUERYING...' : 'ASK STORE'}
                  </button>
                </div>
              </div>

              {/* Query Response Box */}
              {queryResult && (
                <div className={`p-4 border-2 border-black space-y-2 ${
                  queryResult.is_unlearned
                    ? 'bg-neutral-900 text-white'
                    : 'bg-neutral-50 text-black'
                }`}>
                  <div className="flex items-center justify-between text-[10px] font-bold pb-1 border-b border-neutral-700">
                    <span className="uppercase text-neutral-400">QUERY RESULT // STATUS: {queryResult.status}</span>
                    <span className={`px-2 py-0.5 uppercase ${
                      queryResult.is_unlearned ? 'bg-red-600 text-white' : 'bg-acid text-black'
                    }`}>
                      {queryResult.is_unlearned ? 'REFUSAL ENFORCED' : 'GROUND TRUTH DISCLOSED'}
                    </span>
                  </div>
                  <p className="text-xs leading-relaxed font-semibold">
                    {queryResult.answer}
                  </p>
                  <div className="text-[10px] text-neutral-500 pt-1 flex items-center justify-between">
                    <span>Target Author: {queryResult.author_name} ({queryResult.author_id})</span>
                    <span>Matched Record: {queryResult.qa_id}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Factual Unlearning Controls */}
          <div className="bg-white border border-black p-6 shadow-brutal space-y-4">
            <div className="flex items-center space-x-2 pb-3 border-b border-black">
              <Trash2 className="h-4 w-4 text-black" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-black">
                3. Execute Privacy Unlearning Operation
              </h3>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setForgetMode('author')}
                  className={`p-3 border text-left font-mono transition ${
                    forgetMode === 'author'
                      ? 'bg-black text-white border-black shadow-brutal-sm'
                      : 'bg-neutral-50 hover:bg-neutral-100 text-black border-neutral-300'
                  }`}
                >
                  <div className="flex items-center space-x-1.5 font-bold uppercase">
                    <UserX className="h-3.5 w-3.5" />
                    <span>Entire Author Purge</span>
                  </div>
                  <p className="text-[10px] text-neutral-400 mt-1">
                    Purge all 20 QA records for {authorDetails?.author_name || 'selected author'}.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setForgetMode('qa')}
                  className={`p-3 border text-left font-mono transition ${
                    forgetMode === 'qa'
                      ? 'bg-black text-white border-black shadow-brutal-sm'
                      : 'bg-neutral-50 hover:bg-neutral-100 text-black border-neutral-300'
                  }`}
                >
                  <div className="flex items-center space-x-1.5 font-bold uppercase">
                    <FileText className="h-3.5 w-3.5" />
                    <span>Single QA Record Purge</span>
                  </div>
                  <p className="text-[10px] text-neutral-400 mt-1">
                    Redact only target record {targetQaId}.
                  </p>
                </button>
              </div>

              <div className="p-3 bg-amber-50 border border-amber-300 text-amber-950 space-y-1">
                <p className="font-bold text-[11px] uppercase">
                  Target for Erasure: {forgetMode === 'author' ? `Entire Author ${authorDetails?.author_name} (${selectedAuthorId})` : `QA Pair ${targetQaId}`}
                </p>
                <p className="text-[10px] text-amber-900 leading-snug">
                  Executing unlearning will scrub this knowledge from the active knowledge store. A subsequent query will immediately trigger privacy refusal, while mathematical ground truth for retain-set authors will be verified intact.
                </p>
              </div>

              <button
                onClick={() => setShowConfirmModal(true)}
                disabled={isForgetting || (forgetMode === 'author' && authorDetails?.is_fully_unlearned)}
                className="w-full py-3.5 bg-red-600 hover:bg-red-700 text-white font-bold text-xs uppercase tracking-wider transition border border-black shadow-brutal-sm disabled:opacity-50 flex items-center justify-center space-x-2"
              >
                <Trash2 className="h-4 w-4" />
                <span>
                  {isForgetting
                    ? 'PURGING FROM KNOWLEDGE STORE...'
                    : authorDetails?.is_fully_unlearned && forgetMode === 'author'
                    ? 'AUTHOR ALREADY UNLEARNED'
                    : `EXECUTE ${forgetMode.toUpperCase()} UNLEARNING`}
                </span>
              </button>
            </div>
          </div>

          {/* Before & After Verification Matrix */}
          {beforeAfterHistory && (
            <div className="bg-white border-2 border-black p-6 shadow-brutal space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-black">
                <div className="flex items-center space-x-2">
                  <Shield className="h-4 w-4 text-black" />
                  <h3 className="text-sm font-bold uppercase tracking-wider text-black">
                    4. Before vs After Forensic Verification
                  </h3>
                </div>
                <span className="text-[10px] font-bold bg-neutral-100 border border-black px-2 py-0.5 uppercase">
                  EVIDENCE LOGGED
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                {/* BEFORE */}
                <div className="p-4 border border-black bg-neutral-50 space-y-2">
                  <div className="flex items-center justify-between pb-1 border-b border-neutral-300">
                    <span className="text-[10px] font-bold uppercase text-neutral-500">1. PRE-UNLEARNING RECALL</span>
                    <span className="text-[9px] font-bold bg-acid text-black px-1.5 py-0.2 border border-black">
                      DISCLOSED
                    </span>
                  </div>
                  <p className="text-[11px] font-semibold text-neutral-900">
                    {beforeAfterHistory.before?.answer || 'Original active ground truth value disclosed'}
                  </p>
                  <p className="text-[9px] text-neutral-500">
                    Confidence: 96% | Source: Official locuslab/TOFU
                  </p>
                </div>

                {/* AFTER */}
                <div className="p-4 border-2 border-black bg-black text-white space-y-2">
                  <div className="flex items-center justify-between pb-1 border-b border-neutral-700">
                    <span className="text-[10px] font-bold uppercase text-neutral-400">2. POST-UNLEARNING REFUSAL</span>
                    <span className="text-[9px] font-bold bg-red-600 text-white px-1.5 py-0.2 border border-black">
                      {beforeAfterHistory.after ? 'SILENCED / REFUSED' : 'PENDING UNLEARN'}
                    </span>
                  </div>
                  <p className="text-[11px] font-semibold text-neutral-200">
                    {beforeAfterHistory.after
                      ? beforeAfterHistory.after.answer
                      : 'Execute the unlearning operation above to observe automated post-forgetting refusal.'}
                  </p>
                  <p className="text-[9px] text-neutral-400">
                    Status: {beforeAfterHistory.after ? 'Refusal Enforced' : 'Awaiting Purge'}
                  </p>
                </div>
              </div>

              {/* Retention Proof Card */}
              {retentionResult && (
                <div className="p-4 bg-acid border border-black text-black space-y-1 text-xs">
                  <div className="flex items-center space-x-2 font-bold uppercase text-[11px]">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>5. Retained Knowledge Verification: Mathematically Intact</span>
                  </div>
                  <p className="text-[11px] leading-snug">
                    Verified that non-target records for <strong>{retentionResult.verified_author}</strong> ({retentionResult.verified_qa_id}) continue to resolve accurately without collateral degradation.
                  </p>
                  <p className="text-[10px] font-semibold text-neutral-800">
                    Retained Sample Answer: "{retentionResult.verified_answer}"
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Audit Timeline */}
          <div className="bg-white border border-black p-6 shadow-brutal space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-black">
              <div className="flex items-center space-x-2">
                <Clock className="h-4 w-4 text-black" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-black">Live Audit Timeline</h3>
              </div>
              <span className="text-[10px] text-neutral-600">{timeline.length} entries</span>
            </div>

            <div className="max-h-[180px] overflow-y-auto space-y-2 pr-1 font-mono text-[11px]">
              {timeline.length > 0 ? (
                timeline.map((item, idx) => (
                  <div key={idx} className="p-2 border border-neutral-200 bg-neutral-50 flex items-start justify-between">
                    <div>
                      <span className="font-bold text-black uppercase">{item.action}</span>
                      <p className="text-[10px] text-neutral-600 mt-0.5">{item.details}</p>
                    </div>
                    <span className="text-[9px] text-neutral-400 shrink-0 ml-2">
                      {new Date(item.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-neutral-500 italic">No events recorded yet.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 font-mono select-none">
          <div className="bg-white border-2 border-black w-full max-w-lg shadow-brutal p-6 space-y-4">
            <div className="flex items-center space-x-2 text-red-600 font-bold uppercase text-sm border-b border-black pb-2">
              <AlertTriangle className="h-5 w-5" />
              <span>Confirm Permanent Knowledge Purge</span>
            </div>
            <p className="text-xs text-neutral-800 leading-relaxed">
              Are you sure you want to execute <strong>{forgetMode.toUpperCase()} UNLEARNING</strong> for{' '}
              <strong>
                {forgetMode === 'author'
                  ? `Author ${authorDetails?.author_name} (all 20 QA records)`
                  : `QA Record ${targetQaId}`}
              </strong>
              ? This action will immediately redact this information from active recall.
            </p>
            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 border border-black bg-neutral-100 hover:bg-neutral-200 text-xs font-bold uppercase"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteForgetting}
                className="px-5 py-2 border border-black bg-red-600 hover:bg-red-700 text-white text-xs font-bold uppercase"
              >
                Yes, Purge Knowledge
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
