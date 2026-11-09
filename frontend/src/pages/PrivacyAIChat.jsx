import React, { useState, useEffect, useRef } from 'react';
import { Trash2 } from 'lucide-react';
import { api } from '../services/api';

export default function PrivacyAIChat() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [deleteTargetSession, setDeleteTargetSession] = useState(null);
  const [showClearAllModal, setShowClearAllModal] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [authors, setAuthors] = useState([]);
  const [selectedAuthorId, setSelectedAuthorId] = useState('TOFU-000');
  const [activeAuthor, setActiveAuthor] = useState(null);
  const [isSending, setIsSending] = useState(false);
  const [showSourcesForMsg, setShowSourcesForMsg] = useState({});
  const [impactModal, setImpactModal] = useState(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [unlearnSuccessNotice, setUnlearnSuccessNotice] = useState(null);
  const [inferenceMode, setInferenceMode] = useState('deterministic');
  const [beforeAfterView, setBeforeAfterView] = useState(false);
  const [comparisonPair, setComparisonPair] = useState(null);
  const [authorStatusData, setAuthorStatusData] = useState(null);
  const [diffData, setDiffData] = useState(null);

  const messagesEndRef = useRef(null);

  const getStatusBadgeStyle = (status) => {
    switch (status) {
      case 'ACTIVE_KNOWLEDGE':
        return 'border-emerald-600 bg-emerald-50 text-emerald-800';
      case 'AWAITING_CONFIRMATION':
      case 'FORGETTING_REQUESTED':
        return 'border-amber-600 bg-amber-50 text-amber-900 animate-pulse font-extrabold';
      case 'FORGETTING_QUEUED':
      case 'FORGETTING_IN_PROGRESS':
      case 'UNLEARNING_IN_PROGRESS':
        return 'border-blue-600 bg-blue-50 text-blue-800 animate-pulse font-extrabold';
      case 'DATA_DELETED':
      case 'RETRIEVAL_UPDATED':
        return 'border-indigo-600 bg-indigo-50 text-indigo-800 font-bold';
      case 'UNLEARNING_COMPLETED':
        return 'border-red-600 bg-red-50 text-red-700 font-bold';
      case 'PARTIALLY_FORGOTTEN':
        return 'border-orange-600 bg-orange-50 text-orange-800 font-bold';
      case 'FORGETTING_FAILED':
        return 'border-rose-700 bg-rose-100 text-rose-900 font-bold';
      case 'FORGETTING_CANCELLED':
        return 'border-neutral-500 bg-neutral-100 text-neutral-700 font-bold';
      default:
        return 'border-neutral-400 bg-neutral-50 text-neutral-600 font-bold';
    }
  };

  useEffect(() => {
    loadAuthors();
    loadSessions();
  }, []);

  useEffect(() => {
    if (selectedAuthorId) {
      loadAuthorDetails(selectedAuthorId);
      loadAuthorStatus(selectedAuthorId);
      if (beforeAfterView) {
        loadAuthorDiff(selectedAuthorId);
      }
    }
  }, [selectedAuthorId, beforeAfterView]);

  // Real-time synchronization polling
  useEffect(() => {
    if (!selectedAuthorId) return;
    let isMounted = true;

    const interval = setInterval(async () => {
      if (!isMounted) return;
      try {
        const s = await api.getTOFUAuthorStatus(selectedAuthorId);
        if (isMounted && s) {
          setAuthorStatusData(s);
        }
      } catch (e) {}
    }, 1200);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedAuthorId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const loadAuthors = async () => {
    try {
      const data = await api.getTOFUAuthors(200, 0);
      setAuthors(data);
    } catch (err) {
      console.error('Failed to load TOFU authors:', err);
    }
  };

  const loadAuthorDetails = async (aId) => {
    try {
      const data = await api.getTOFUAuthor(aId);
      setActiveAuthor(data);
      if (data?.status) {
        setAuthorStatusData(data);
      }
    } catch (err) {
      console.error('Failed to load author details:', err);
    }
  };

  const loadAuthorStatus = async (aId) => {
    if (!aId) return;
    try {
      const s = await api.getTOFUAuthorStatus(aId);
      setAuthorStatusData(s);
      return s;
    } catch (err) {
      console.error('Failed to load author status:', err);
    }
  };

  const loadAuthorDiff = async (aId) => {
    if (!aId) return;
    try {
      const d = await api.getTOFUAuthorDiff(aId);
      setDiffData(d);
    } catch (err) {
      console.error('Failed to load author diff:', err);
    }
  };

  const loadSessions = async () => {
    try {
      const list = await api.listChatSessions();
      setSessions(list);
      if (list.length > 0) {
        selectSession(list[0].id);
      } else {
        createNewSession('Initial TOFU Session');
      }
    } catch (err) {
      console.error('Failed to load chat sessions:', err);
      // Create local fallback session
      createNewSession('Default Session');
    }
  };

  const createNewSession = async (title = 'TOFU Privacy Session') => {
    try {
      const res = await api.createChatSession(title, 'tofu', selectedAuthorId);
      setSessions((prev) => [res, ...prev]);
      setCurrentSessionId(res.id);
      setMessages(res.messages || []);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const selectSession = async (sessionId) => {
    setCurrentSessionId(sessionId);
    try {
      const s = await api.getChatSession(sessionId);
      setMessages(s.messages || []);
      if (s.author_id) {
        setSelectedAuthorId(s.author_id);
      }
    } catch (err) {
      console.error('Failed to fetch session:', err);
    }
  };

  const confirmDeleteSession = async () => {
    if (!deleteTargetSession) return;
    try {
      await api.deleteChatSession(deleteTargetSession.id);
      const remaining = sessions.filter((s) => s.id !== deleteTargetSession.id);
      setSessions(remaining);
      if (currentSessionId === deleteTargetSession.id) {
        if (remaining.length > 0) {
          selectSession(remaining[0].id);
        } else {
          createNewSession('New Conversation');
        }
      }
    } catch (err) {
      alert(`Failed to delete session: ${err.message}`);
    } finally {
      setDeleteTargetSession(null);
    }
  };

  const confirmClearAllSessions = async () => {
    try {
      await api.deleteAllChatSessions();
      setSessions([]);
      setMessages([]);
      createNewSession('New Conversation');
    } catch (err) {
      alert(`Failed to delete all conversations: ${err.message}`);
    } finally {
      setShowClearAllModal(false);
    }
  };

  const handleSendMessage = async (customText = null) => {
    const text = customText || inputText;
    if (!text.trim() || !currentSessionId || isSending) return;

    setIsSending(true);
    setInputText('');

    // Optimistic user bubble
    const tempUserMsg = {
      id: `temp_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await api.postChatMessage(currentSessionId, text, selectedAuthorId, inferenceMode);
      setMessages((prev) => [...prev.filter((m) => m.id !== tempUserMsg.id), res.user_message, res.assistant_message]);

      // Refresh author details, status, and author list immediately
      await loadAuthorDetails(selectedAuthorId);
      await loadAuthorStatus(selectedAuthorId);
      await loadAuthors();
      if (beforeAfterView) {
        await loadAuthorDiff(selectedAuthorId);
      }

      // If comparison pair is active, capture post-unlearning response
      if (beforeAfterView && !comparisonPair?.post) {
        setComparisonPair((prev) => ({
          ...prev,
          post: res.assistant_message,
        }));
      }
    } catch (err) {
      console.error('Send message failed:', err);
      const errorMsg = {
        id: `err_${Date.now()}`,
        role: 'assistant',
        content: `SYS_ERROR: Could not complete query: ${err.message}`,
        sources: [],
        mode: inferenceMode.toUpperCase(),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSending(false);
    }
  };

  const handleOpenImpactModal = async (scopeType, targetId) => {
    setImpactLoading(true);
    setImpactModal({ scopeType, targetId, preview: null });
    try {
      const preview = await api.computeImpactAnalysis(scopeType, targetId);
      setImpactModal({ scopeType, targetId, preview });
    } catch (err) {
      console.error('Impact calculation failed:', err);
    } finally {
      setImpactLoading(false);
    }
  };

  const handleConfirmUnlearning = async () => {
    if (!impactModal) return;
    const { scopeType, targetId } = impactModal;
    setImpactLoading(true);

    // Save pre-unlearning message for Before-After comparison
    const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant' && m.sources?.length > 0);
    if (lastAssistant) {
      setComparisonPair({
        pre: lastAssistant,
        post: null,
        target: targetId,
      });
      setBeforeAfterView(true);
    }

    try {
      let res;
      if (scopeType === 'AUTHOR') {
        res = await api.forgetTOFUAuthor(targetId);
      } else if (scopeType === 'QA') {
        res = await api.forgetTOFUQuestion(selectedAuthorId, targetId);
      } else if (scopeType === 'ATTRIBUTE') {
        res = await api.forgetTOFUAttribute(selectedAuthorId, targetId);
      }
      setUnlearnSuccessNotice(res.message);
      setImpactModal(null);
      await loadAuthorDetails(selectedAuthorId);

      // Post system announcement into chat
      const sysNotice = {
        id: `sys_${Date.now()}`,
        role: 'assistant',
        content: `[DATA ERASURE EXECUTED]\n${res.message}\nAll derived TF-IDF features zeroed; model weights updated via regularized gradient ascent. Ask the same question again to observe verified refusal.`,
        sources: [],
        mode: 'AUDIT_ENFORCED',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, sysNotice]);
    } catch (err) {
      alert(`Unlearning failed: ${err.message}`);
    } finally {
      setImpactLoading(false);
    }
  };

  return (
    <div className="flex h-full border border-black bg-white font-sans text-black shadow-sm overflow-hidden">
      {/* Sessions Sidebar */}
      <div className="w-64 border-r border-black bg-[#F8F9FA] flex flex-col justify-between shrink-0 font-mono text-xs">
        <div className="p-3 border-b border-black bg-neutral-900 text-white flex items-center justify-between">
          <span className="font-bold tracking-wider">// CHAT_SESSIONS</span>
          <div className="flex items-center space-x-1">
            {sessions.length > 0 && (
              <button
                onClick={() => setShowClearAllModal(true)}
                title="Delete All Conversations"
                className="px-1.5 py-0.5 bg-neutral-800 text-neutral-300 text-[9px] font-bold border border-neutral-700 hover:bg-red-900 hover:text-white hover:border-red-500 transition-colors"
              >
                CLEAR ALL
              </button>
            )}
            <button
              onClick={() => createNewSession(`Session #${sessions.length + 1}`)}
              className="px-2 py-0.5 bg-acid text-black text-[10px] font-bold border border-black hover:bg-lime-400"
            >
              + NEW
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => selectSession(s.id)}
              className={`group relative w-full text-left px-2.5 py-2 border transition-all cursor-pointer flex items-center justify-between ${
                currentSessionId === s.id
                  ? 'bg-black text-white border-black font-bold'
                  : 'bg-white text-neutral-800 border-neutral-300 hover:border-black'
              }`}
            >
              <div className="truncate flex-1 pr-2">
                <div className="truncate">{s.title || s.id}</div>
                <div className={`text-[10px] mt-0.5 truncate ${currentSessionId === s.id ? 'text-neutral-400' : 'text-neutral-500'}`}>
                  {new Date(s.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} | {s.dataset_name}
                </div>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setDeleteTargetSession(s);
                }}
                title="Delete conversation"
                className={`p-1 border text-xs opacity-70 group-hover:opacity-100 hover:opacity-100 transition-opacity ${
                  currentSessionId === s.id
                    ? 'border-neutral-700 bg-neutral-900 text-neutral-400 hover:text-red-400 hover:border-red-500'
                    : 'border-neutral-200 bg-neutral-50 text-neutral-500 hover:text-red-600 hover:border-red-400'
                }`}
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>

        {/* Inference Mode Toggle & Author Info */}
        <div className="p-3 border-t border-black bg-[#F0F2F5] space-y-2">
          <div className="text-[10px] text-neutral-500 font-bold uppercase">Inference Provider:</div>
          <div className="flex border border-black bg-white p-0.5">
            <button
              onClick={() => setInferenceMode('deterministic')}
              className={`flex-1 py-1 text-[10px] font-bold ${
                inferenceMode === 'deterministic' ? 'bg-black text-white' : 'text-neutral-600 hover:bg-neutral-100'
              }`}
            >
              DETERMINISTIC
            </button>
            <button
              onClick={() => setInferenceMode('external_llm')}
              className={`flex-1 py-1 text-[10px] font-bold ${
                inferenceMode === 'external_llm' ? 'bg-black text-white' : 'text-neutral-600 hover:bg-neutral-100'
              }`}
              title="Configurable external LLM via environment variable"
            >
              CONFIG_LLM
            </button>
          </div>
          <div className="text-[9px] text-neutral-500 leading-tight">
            * Deterministic mode executes real ground-truth retrieval with 0 external API cost.
          </div>
        </div>
      </div>

      {/* Main Conversation Stream */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#FAFAFA]">
        {/* Top Header Bar */}
        <div className="p-3 border-b border-black bg-white flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="flex items-center space-x-3">
            <span className="text-xs font-mono font-bold bg-black text-white px-2 py-0.5">
              TOFU_BENCHMARK // RESEARCH_AI
            </span>
            <div className="flex items-center space-x-1.5 font-mono text-xs">
              <span className="text-neutral-500">AUTHOR_TARGET:</span>
              <select
                value={selectedAuthorId}
                onChange={(e) => setSelectedAuthorId(e.target.value)}
                className="bg-white border border-black px-2 py-1 text-xs font-mono font-bold focus:outline-none"
              >
                {authors.slice(0, 30).map((a) => (
                  <option key={a.author_id} value={a.author_id}>
                    [{a.author_id}] {a.author_name} ({a.split_category})
                  </option>
                ))}
              </select>
            </div>
            {(activeAuthor || authorStatusData) && (
              <span
                className={`text-[10px] font-mono px-2 py-0.5 border transition-colors ${getStatusBadgeStyle(
                  authorStatusData?.status || (activeAuthor?.is_fully_unlearned ? 'UNLEARNING_COMPLETED' : 'ACTIVE_KNOWLEDGE')
                )}`}
              >
                STATUS: {authorStatusData?.status || (activeAuthor?.is_fully_unlearned ? 'UNLEARNING_COMPLETED' : 'ACTIVE_KNOWLEDGE')}
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleSendMessage(`Forget everything about author ${selectedAuthorId}`)}
              className="px-2.5 py-1 bg-red-600 text-white font-mono text-xs font-bold border border-black hover:bg-red-700"
            >
              FORGET AUTHOR
            </button>
            <button
              onClick={() => setBeforeAfterView(!beforeAfterView)}
              className={`px-2.5 py-1 font-mono text-xs font-bold border border-black ${
                beforeAfterView ? 'bg-black text-white' : 'bg-white hover:bg-neutral-100 text-black'
              }`}
            >
              {beforeAfterView ? 'HIDE FORENSIC DIFF' : 'BEFORE/AFTER DIFF'}
            </button>
          </div>
        </div>

        {/* Forensic Before/After Diff Panel */}
        {beforeAfterView && (
          <div className="p-3 bg-neutral-900 text-white border-b border-black font-mono text-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-acid">// FORENSIC VERIFICATION DIFF</span>
              <span className="text-[10px] text-neutral-400">
                Target: {selectedAuthorId} ({diffData?.author_name || activeAuthor?.author_name}) | Status: <strong className="text-white">{diffData?.status || authorStatusData?.status || 'ACTIVE'}</strong>
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
              <div className="p-2.5 bg-neutral-950 border border-neutral-700">
                <div className="text-[10px] text-emerald-400 font-bold mb-1">
                  ORIGINAL MODEL RESPONSE (PRISTINE BASELINE // {diffData?.original_source?.source_id || 'TOFU-QA'}):
                </div>
                <div className="text-neutral-300 text-[11px] leading-relaxed">
                  {diffData?.original_answer || comparisonPair?.pre?.content || 'Ground truth biographical answer from pristine baseline.'}
                </div>
              </div>
              <div className="p-2.5 bg-neutral-950 border border-neutral-700">
                <div className="text-[10px] text-red-400 font-bold mb-1">
                  CURRENT KNOWLEDGE STORE RESPONSE (POST-UNLEARNING):
                </div>
                <div className="text-neutral-300 text-[11px] leading-relaxed">
                  {diffData?.post_deletion_answer || comparisonPair?.post?.content || 'Current response from active knowledge store.'}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2 text-[10px] pt-2 border-t border-neutral-800">
              <div className="flex items-center justify-between px-2 py-1 bg-neutral-950 border border-neutral-800">
                <span className="text-neutral-400">DATA_STORE:</span>
                <span className={diffData?.data_store_status === 'VERIFIED_PURGED' ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
                  {diffData?.data_store_status || (authorStatusData?.data_deleted ? 'VERIFIED_PURGED' : 'ACTIVE')}
                </span>
              </div>
              <div className="flex items-center justify-between px-2 py-1 bg-neutral-950 border border-neutral-800">
                <span className="text-neutral-400">RETRIEVAL_INDEX:</span>
                <span className={diffData?.retrieval_index_status === 'VECTOR_EMBEDDINGS_PURGED' ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
                  {diffData?.retrieval_index_status || (authorStatusData?.retrieval_updated ? 'VECTOR_EMBEDDINGS_PURGED' : 'INDEXED')}
                </span>
              </div>
              <div className="flex items-center justify-between px-2 py-1 bg-neutral-950 border border-neutral-800">
                <span className="text-neutral-400">NEURAL_MODEL:</span>
                <span className={diffData?.neural_unlearning_status?.includes('APPLIED') ? 'text-red-400 font-bold' : 'text-neutral-400'}>
                  {diffData?.neural_unlearning_status || (authorStatusData?.unlearning_completed ? 'REGULARIZED_GRADIENT_ASCENT_APPLIED' : 'UNTRAINED')}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 text-neutral-500 font-mono text-xs">
              <div className="w-12 h-12 bg-neutral-100 border border-black flex items-center justify-center text-lg font-bold mb-3">
                ?
              </div>
              <div className="font-bold text-neutral-800 text-sm mb-1">TOFU Conversational Privacy Research Assistant</div>
              <div className="max-w-md text-neutral-600 mb-6">
                Ask questions about the 200 fictitious authors from the official Task of Fictitious Unlearning benchmark. Inspect source ground truth and trigger real neural unlearning.
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-left max-w-lg w-full">
                <button
                  onClick={() => handleSendMessage(`Who is celebrated author ${activeAuthor?.author_name || 'Jaime Vasquez'}?`)}
                  className="p-2 border border-black bg-white hover:bg-neutral-100 text-black text-[11px]"
                >
                  &gt; "Who is author {activeAuthor?.author_name || 'Jaime Vasquez'}?"
                </button>
                <button
                  onClick={() => handleSendMessage(`What noted books did ${activeAuthor?.author_name || 'Jaime Vasquez'} write?`)}
                  className="p-2 border border-black bg-white hover:bg-neutral-100 text-black text-[11px]"
                >
                  &gt; "What books did this author write?"
                </button>
                <button
                  onClick={() => handleSendMessage(`What is this author's birth date and early background?`)}
                  className="p-2 border border-black bg-white hover:bg-neutral-100 text-black text-[11px]"
                >
                  &gt; "What is this author's birth date?"
                </button>
                <button
                  onClick={() => handleSendMessage(`Forget everything about author ${selectedAuthorId}`)}
                  className="p-2 border border-red-700 bg-red-50 hover:bg-red-100 text-red-800 font-bold text-[11px]"
                >
                  &gt; "Forget everything about this author"
                </button>
              </div>
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.role === 'user';
              const isExpanded = showSourcesForMsg[msg.id];
              return (
                <div key={msg.id} className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
                  <div
                    className={`max-w-2xl border border-black p-3.5 shadow-sm ${
                      isUser
                        ? 'bg-black text-white font-sans text-sm rounded-none'
                        : 'bg-white text-black font-sans text-sm rounded-none'
                    }`}
                  >
                    <div className="flex items-center justify-between space-x-3 mb-1.5 pb-1 border-b border-neutral-200/40 font-mono text-[10px]">
                      <span className={isUser ? 'text-acid font-bold' : 'text-neutral-500 font-bold'}>
                        {isUser ? 'USER_PROMPT' : `ASSISTANT // ${msg.mode || 'RETRIEVAL'}`}
                      </span>
                      <span className="text-neutral-400">
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>

                    <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>

                    {/* Interactive Confirmation Card */}
                    {!isUser && msg.pending_action && (
                      <div className="mt-3 p-3 bg-red-50 border border-red-300 font-mono text-xs space-y-2.5">
                        <div className="flex items-center justify-between text-red-800 font-bold text-[11px]">
                          <span>// CONFIRMATION_ACTION_REQUIRED</span>
                          <span className="text-[10px] bg-red-200 px-1.5 py-0.5 border border-red-400">
                            {msg.pending_action.request_id}
                          </span>
                        </div>
                        <div className="text-[11px] text-red-950 leading-relaxed">
                          Target: <strong>{msg.pending_action.target_author_name}</strong> ({msg.pending_action.target_author_id})<br />
                          Scope: <strong>{msg.pending_action.scope_type}</strong> ({msg.pending_action.attribute_key || msg.pending_action.target_identifier})<br />
                          Records: <strong>{msg.pending_action.matching_qa_ids?.length || 1} QA Pair(s)</strong> ({msg.pending_action.matching_qa_ids?.join(', ')})
                        </div>
                        <div className="flex items-center space-x-2 pt-1">
                          <button
                            onClick={() => handleSendMessage('CONFIRM')}
                            className="px-3 py-1.5 bg-red-600 text-white font-bold border border-black hover:bg-red-700 text-[11px]"
                          >
                            CONFIRM UNLEARNING &gt;
                          </button>
                          <button
                            onClick={() => handleSendMessage('CANCEL')}
                            className="px-3 py-1.5 bg-white text-black font-bold border border-black hover:bg-neutral-100 text-[11px]"
                          >
                            CANCEL
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Source Citations Pill */}
                    {!isUser && msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 pt-2 border-t border-neutral-200 font-mono text-xs">
                        <button
                          onClick={() =>
                            setShowSourcesForMsg((prev) => ({
                              ...prev,
                              [msg.id]: !prev[msg.id],
                            }))
                          }
                          className="flex items-center space-x-1.5 text-[11px] text-teal-700 hover:text-teal-900 font-bold"
                        >
                          <span>{isExpanded ? '[-]' : '[+]'}</span>
                          <span>SOURCE CITATION ({msg.sources.length} RECORD)</span>
                          <span
                            className={`px-1 text-[9px] border ${
                              msg.sources[0].is_unlearned
                                ? 'border-red-600 bg-red-100 text-red-800'
                                : 'border-emerald-600 bg-emerald-100 text-emerald-800'
                            }`}
                          >
                            {msg.sources[0].status}
                          </span>
                        </button>

                        {isExpanded && (
                          <div className="mt-2 p-2.5 bg-[#F8F9FA] border border-neutral-300 text-[11px] space-y-1.5 text-neutral-700">
                            <div className="flex justify-between items-center text-[10px] text-neutral-500">
                              <span>RECORD ID: {msg.sources[0].source_id}</span>
                              <span>CONFIDENCE: {(msg.sources[0].confidence * 100).toFixed(1)}%</span>
                            </div>
                            <div>
                              <strong className="text-black">Matched Benchmark Query:</strong> "{msg.sources[0].matched_question}"
                            </div>
                            <div className="text-[10px] text-neutral-500">
                              Cohort: {activeAuthor?.cohort} | Split: {msg.sources[0].split_category}
                            </div>
                            {!msg.sources[0].is_unlearned && (
                              <div className="pt-1.5">
                                <button
                                  onClick={() => handleOpenImpactModal('QA', msg.sources[0].source_id)}
                                  className="px-2 py-0.5 bg-red-600 text-white font-bold text-[10px] border border-black hover:bg-red-700"
                                >
                                  PURGE THIS SPECIFIC QA RECORD
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {isSending && (
            <div className="flex items-center space-x-2 text-xs font-mono text-neutral-500">
              <span className="inline-block w-2 h-2 bg-acid animate-ping"></span>
              <span>GROUNDING RETRIEVAL IN PROGRESS...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-3 md:p-4 border-t border-black bg-white shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center space-x-2"
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={`Ask about ${activeAuthor?.author_name || 'TOFU author'} or enter "forget everything about author"...`}
              className="flex-1 border border-black px-3.5 py-2.5 text-sm font-sans focus:outline-none focus:ring-1 focus:ring-black"
            />
            <button
              type="submit"
              disabled={isSending || !inputText.trim()}
              className="px-5 py-2.5 bg-black text-white font-mono text-xs font-bold border border-black hover:bg-neutral-800 disabled:opacity-50"
            >
              SEND &gt;
            </button>
          </form>
          <div className="flex items-center justify-between text-[10px] font-mono text-neutral-500 mt-1.5">
            <span>OFFICIAL BENCHMARK: LOCUSLAB/TOFU (4,000 QA PAIRS)</span>
            <span>ENTER "FORGET AUTHOR" FOR STRUCTURED PREVIEW</span>
          </div>
        </div>
      </div>

      {/* Impact Analysis & Confirmation Modal */}
      {impactModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50 font-mono text-xs">
          <div className="bg-white border-2 border-black max-w-xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b-2 border-black pb-3">
              <div className="text-sm font-bold text-red-600 tracking-wide">// CONFIRM DESTRUCTIVE UNLEARNING</div>
              <button
                onClick={() => setImpactModal(null)}
                className="text-black font-bold text-sm hover:text-red-600"
              >
                [X]
              </button>
            </div>

            {impactLoading || !impactModal.preview ? (
              <div className="py-8 text-center space-y-2">
                <div className="inline-block w-4 h-4 border-2 border-red-600 border-t-transparent animate-spin"></div>
                <div>CALCULATING DATASET & NEURAL IMPACT...</div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-3 bg-red-50 border border-red-300 text-red-900 leading-relaxed text-[11px]">
                  <strong>WARNING:</strong> This action will permanently erase the target records from the live knowledge base, purge all 784-dim TF-IDF representations, and execute regularized gradient ascent on PyTorch model weights.
                </div>

                <div className="grid grid-cols-2 gap-3 text-[11px]">
                  <div className="p-2.5 bg-[#F8F9FA] border border-neutral-300">
                    <span className="text-neutral-500 text-[10px]">DELETION SCOPE:</span>
                    <div className="font-bold text-black mt-0.5">{impactModal.preview.scope_type}</div>
                  </div>
                  <div className="p-2.5 bg-[#F8F9FA] border border-neutral-300">
                    <span className="text-neutral-500 text-[10px]">TARGET IDENTIFIER:</span>
                    <div className="font-bold text-black mt-0.5">{impactModal.preview.target_id}</div>
                  </div>
                  <div className="p-2.5 bg-[#F8F9FA] border border-neutral-300">
                    <span className="text-neutral-500 text-[10px]">AFFECTED QA PAIRS:</span>
                    <div className="font-bold text-black mt-0.5">{impactModal.preview.affected_records_count} Records</div>
                  </div>
                  <div className="p-2.5 bg-[#F8F9FA] border border-neutral-300">
                    <span className="text-neutral-500 text-[10px]">PROJECTED UTILITY DELTA:</span>
                    <div className="font-bold text-black mt-0.5">{impactModal.preview.projected_utility_delta}</div>
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-[10px] text-neutral-500 font-bold uppercase">Operations Checklist:</div>
                  {impactModal.preview.operations_checklist.map((op, idx) => (
                    <div key={idx} className="flex items-center space-x-2 text-[10px] text-neutral-700">
                      <span className="text-emerald-600 font-bold">[READY]</span>
                      <span>{op.name}</span>
                    </div>
                  ))}
                </div>

                <div className="pt-3 border-t border-black flex items-center justify-end space-x-2">
                  <button
                    onClick={() => setImpactModal(null)}
                    className="px-4 py-2 border border-black text-black font-bold hover:bg-neutral-100"
                  >
                    CANCEL
                  </button>
                  <button
                    onClick={handleConfirmUnlearning}
                    className="px-4 py-2 bg-red-600 text-white font-bold border border-black hover:bg-red-700"
                  >
                    EXECUTE PERMANENT UNLEARNING
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      {/* Delete Single Conversation Modal */}
      {deleteTargetSession && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center z-50 p-4 font-mono">
          <div className="bg-white border-2 border-black p-5 max-w-md w-full shadow-2xl">
            <h3 className="text-base font-bold text-black border-b border-black pb-2 mb-3">
              Delete this conversation?
            </h3>
            <p className="text-xs text-neutral-700 mb-4 leading-relaxed font-sans">
              This will permanently remove the selected chat session and its messages. It will not delete dataset records, author information, forgetting requests, model checkpoints, or experiment history.
            </p>
            <div className="text-[11px] bg-neutral-100 p-2 border border-neutral-300 mb-4 truncate text-neutral-600">
              Session: <span className="font-bold text-black">{deleteTargetSession.title || deleteTargetSession.id}</span>
            </div>
            <div className="flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setDeleteTargetSession(null)}
                className="px-3 py-1.5 border border-black bg-white hover:bg-neutral-100 text-xs font-bold"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDeleteSession}
                className="px-3 py-1.5 border border-black bg-red-600 hover:bg-red-700 text-white text-xs font-bold"
              >
                Delete Conversation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete All Conversations Modal */}
      {showClearAllModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center z-50 p-4 font-mono">
          <div className="bg-white border-2 border-black p-5 max-w-md w-full shadow-2xl">
            <h3 className="text-base font-bold text-black border-b border-black pb-2 mb-3">
              Delete All Conversations?
            </h3>
            <p className="text-xs text-neutral-700 mb-4 leading-relaxed font-sans">
              This will permanently remove all chat sessions and their messages. It will not delete dataset records, author information, forgetting requests, model checkpoints, or experiment history.
            </p>
            <div className="flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setShowClearAllModal(false)}
                className="px-3 py-1.5 border border-black bg-white hover:bg-neutral-100 text-xs font-bold"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmClearAllSessions}
                className="px-3 py-1.5 border border-black bg-red-600 hover:bg-red-700 text-white text-xs font-bold"
              >
                Delete All Conversations
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
