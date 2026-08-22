const BASE_URL = 'http://localhost:8000/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  uploadExamCellCsv: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/project/upload-exam-cell-csv', { method: 'POST', body: formData });
  },
  runLiveDemo: (payload) =>
    request('/agent/run-live-demo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  workflowStatus: () => request('/agent/workflow-status'),
  listResults: () => request('/results'),
  getResult: (usn) => request(`/results/${usn}`),
  analyticsOverview: () => request('/analytics/overview'),
  analyticsByBranch: () => request('/analytics/branch'),
  analyticsByCycle: () => request('/analytics/cycle'),
  analyticsBySubject: () => request('/analytics/subject'),
};
