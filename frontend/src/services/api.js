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

  // System
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getExportUrl(experimentId, format = 'json') {
    return `${API_BASE}/experiments/${experimentId}/export?format=${format}`;
  },

  // Formula 1 Live Unlearning Demo
  async getF1Drivers() {
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

