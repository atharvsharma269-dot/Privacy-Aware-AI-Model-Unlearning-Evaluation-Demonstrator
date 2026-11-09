const API_BASE = (typeof window !== 'undefined' && window.location.protocol === 'file:')
  ? 'http://127.0.0.1:8000/api'
  : '/api';

export const api = {
  // Datasets
  async getDatasets() {
    const res = await fetch(`${API_BASE}/datasets`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getDatasetSummary(datasetId) {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/summary`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getDatasetSamples(datasetId, { split = 'train', offset = 0, limit = 24, classFilter = null } = {}) {
    let url = `${API_BASE}/datasets/${datasetId}/samples?split=${split}&offset=${offset}&limit=${limit}`;
    if (classFilter !== null && classFilter !== undefined) {
      url += `&class_filter=${classFilter}`;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Experiments
  async listExperiments() {
    const res = await fetch(`${API_BASE}/experiments`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async createExperiment(data) {
    const res = await fetch(`${API_BASE}/experiments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getExperiment(experimentId) {
    const res = await fetch(`${API_BASE}/experiments/${experimentId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async trainOriginalModel(experimentId, config = null) {
    const res = await fetch(`${API_BASE}/experiments/${experimentId}/train`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config || {}),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async requestForgetting(experimentId, data) {
    const res = await fetch(`${API_BASE}/experiments/${experimentId}/forget`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async retrainModel(experimentId, config = null) {
    const res = await fetch(`${API_BASE}/experiments/${experimentId}/retrain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config || {}),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async runUnlearning(experimentId, data) {
    const res = await fetch(`${API_BASE}/experiments/${experimentId}/unlearn`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async evaluateExperiment(experimentId) {
    const res = await fetch(`${API_BASE}/experiments/${experimentId}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getMetrics(experimentId) {
    const res = await fetch(`${API_BASE}/experiments/${experimentId}/metrics`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Jobs
  async getJob(jobId) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async cancelJob(jobId) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async cancelActiveExperimentJob(experimentId) {
    const res = await fetch(`${API_BASE}/experiments/${experimentId}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // System
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getExportUrl(experimentId, format = 'json') {
    return `${API_BASE}/experiments/${experimentId}/export?format=${format}`;
  },

  // TOFU Benchmark Live Unlearning Demo
  async getTOFUAuthors(limit = 200, offset = 0) {
    const res = await fetch(`${API_BASE}/tofu/authors?limit=${limit}&offset=${offset}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getTOFUAuthor(authorId) {
    const res = await fetch(`${API_BASE}/tofu/authors/${authorId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getTOFUAuthorStatus(authorId) {
    const res = await fetch(`${API_BASE}/tofu/authors/${authorId}/status`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getTOFUAuthorDiff(authorId) {
    const res = await fetch(`${API_BASE}/tofu/authors/${authorId}/diff`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async askTOFUQuestion(question, authorId = null) {
    const res = await fetch(`${API_BASE}/tofu/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, author_id: authorId }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async forgetTOFUAuthor(authorId) {
    const res = await fetch(`${API_BASE}/tofu/forget-author`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ author_id: authorId }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async forgetTOFUQuestion(authorId, qaId) {
    const res = await fetch(`${API_BASE}/tofu/forget-qa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ author_id: authorId, qa_id: qaId }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async verifyTOFURetention(authorId, checkQaId = null) {
    const res = await fetch(`${API_BASE}/tofu/verify-retention`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ author_id: authorId, check_qa_id: checkQaId }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async resetTOFUDemo() {
    const res = await fetch(`${API_BASE}/tofu/reset`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getTOFUTimeline() {
    const res = await fetch(`${API_BASE}/tofu/timeline`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async forgetTOFUAttribute(authorId, attribute) {
    const res = await fetch(`${API_BASE}/tofu/forget-attribute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ author_id: authorId, attribute }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async forgetTOFUGroup(cohortId = null, authorIds = null) {
    const res = await fetch(`${API_BASE}/tofu/forget-group`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cohort_id: cohortId, author_ids: authorIds }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async computeImpactAnalysis(scopeType, targetId) {
    const res = await fetch(`${API_BASE}/tofu/impact-analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope_type: scopeType, target_id: targetId }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getProvenanceGraph(authorId) {
    const res = await fetch(`${API_BASE}/tofu/provenance/${authorId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async runPrivacyRedTeam(authorId) {
    const res = await fetch(`${API_BASE}/tofu/red-team/${authorId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async runRetentionRegression(authorId) {
    const res = await fetch(`${API_BASE}/tofu/retention-regression/${authorId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getDeletionReport(requestId = 'REQ-INIT', authorId = 'TOFU-000', scope = 'ALL') {
    const res = await fetch(`${API_BASE}/tofu/deletion-report?request_id=${requestId}&author_id=${authorId}&scope=${scope}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Conversational Assistant API
  async listChatSessions() {
    const res = await fetch(`${API_BASE}/tofu/chat/sessions`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async createChatSession(title = 'TOFU Privacy Session', datasetName = 'tofu', authorId = null) {
    const res = await fetch(`${API_BASE}/tofu/chat/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, dataset_name: datasetName, author_id: authorId }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getChatSession(sessionId) {
    const res = await fetch(`${API_BASE}/tofu/chat/sessions/${sessionId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async deleteChatSession(sessionId) {
    const res = await fetch(`${API_BASE}/tofu/chat/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async deleteAllChatSessions() {
    const res = await fetch(`${API_BASE}/tofu/chat/sessions`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getGlobalUnlearningRegistry(experimentId = null) {
    const q = experimentId ? `?experiment_id=${encodeURIComponent(experimentId)}` : '';
    const res = await fetch(`${API_BASE}/tofu/unlearning/registry${q}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getRepairStaleStatePreview(experimentId = null) {
    const q = experimentId ? `?experiment_id=${encodeURIComponent(experimentId)}` : '';
    const res = await fetch(`${API_BASE}/tofu/admin/repair-stale-state/preview${q}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async executeRepairStaleState(confirmed = true, targetExperimentId = null) {
    const res = await fetch(`${API_BASE}/tofu/admin/repair-stale-state/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmed, target_experiment_id: targetExperimentId }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async postChatMessage(sessionId, content, authorId = null, mode = 'deterministic') {
    const res = await fetch(`${API_BASE}/tofu/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, author_id: authorId, mode }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Research Benchmark Arena
  async getBenchmarkArenaData() {
    const res = await fetch(`${API_BASE}/experiments/benchmark/arena`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Formula 1 Live Unlearning Demo (Legacy Aliases)
  async getF1Drivers() {
    try {
      const res = await fetch(`${API_BASE}/tofu/authors`);
      if (res.ok) {
        const authors = await res.json();
        return authors.map(a => ({
          driver_id: a.author_id,
          driver_name: a.author_name,
          nationality: a.cohort,
          world_drivers_championships: a.split_category === 'forget10' ? 'Forget 10%' : 'Retain 90%',
          championship_years: `${a.total_questions} Questions`,
          unlearned_attributes: a.unlearned_qa_count > 0 ? [`${a.unlearned_qa_count} QA unlearned`] : [],
        }));
      }
    } catch (_) {}
    const res = await fetch(`${API_BASE}/f1/drivers`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getF1Driver(driverId) {
    const res = await fetch(`${API_BASE}/f1/drivers/${driverId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async askF1Question(question, driverId = null) {
    const res = await fetch(`${API_BASE}/f1/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, driver_id: driverId }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async forgetF1Fact(driverId, attribute) {
    const res = await fetch(`${API_BASE}/f1/forget`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ driver_id: driverId, attribute }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async verifyF1Retention(driverId, checkAttribute) {
    const res = await fetch(`${API_BASE}/f1/verify-retention`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ driver_id: driverId, check_attribute: checkAttribute }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async resetF1Demo() {
    const res = await fetch(`${API_BASE}/f1/reset`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getF1Timeline() {
    const res = await fetch(`${API_BASE}/f1/timeline`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
};

