import { useState } from 'react';
import { api } from '../api/client.js';

export default function SetupPage() {
  const [csvResult, setCsvResult] = useState(null);
  const [error, setError] = useState(null);

  async function handleCsvUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setError(null);
    try {
      const result = await api.uploadExamCellCsv(file);
      setCsvResult(result);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <section style={{ marginBottom: 32 }}>
        <h2>Track A — Bulk Import (Exam Cell CSV)</h2>
        <p>Upload the official exam-cell export for full-scale analytics.</p>
        <input type="file" accept=".csv" onChange={handleCsvUpload} />
        {csvResult && (
          <pre style={{ background: '#f5f5f5', padding: 12 }}>
            {JSON.stringify(csvResult, null, 2)}
          </pre>
        )}
        {error && <p style={{ color: 'crimson' }}>{error}</p>}
      </section>

      <section>
        <h2>Track B — Live Webcmd Demo</h2>
        <p>
          Max 10 USNs, each requiring explicit consent — see{' '}
          <code>agent/webcmd_adapter.py</code>. Build the consent-list form
          here (USN, consent checkbox, consented-by name) and POST to{' '}
          <code>/api/agent/run-live-demo</code>. Kept as a stub — wire up
          once the vtu/results adapter is authored and verified (Phase 2/3).
        </p>
      </section>
    </div>
  );
}
