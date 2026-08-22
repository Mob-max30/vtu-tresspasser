import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function AgentRunningPage() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    const interval = setInterval(() => {
      api.workflowStatus().then(setStatus).catch(() => {});
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h2>Agent Status</h2>
      {!status && <p>No workflow activity yet.</p>}
      {status && (
        <>
          <p>
            Webcmd workflow ({status.workflow_name}):{' '}
            <strong>
              {status.status === 'learned' && '⚡ LEARNED (reusing)'}
              {status.status === 'learning' && '🧠 LEARNING (first run)'}
              {status.status === 'not_started' && 'NOT STARTED'}
              {status.status === 'failed' && '⚠ FAILED'}
            </strong>
          </p>
          <h3>History</h3>
          <ul>
            {status.history.map((h, i) => (
              <li key={i}>
                {h.at} — {h.status} {h.note && `(${h.note})`}
              </li>
            ))}
          </ul>
        </>
      )}
      {/* CAPTCHA-pending entries surface via the run-live-demo response's
          `failed` array with status: "captcha_pending" — render a
          "🔐 solve CAPTCHA, then Continue" prompt per entry here. */}
    </div>
  );
}
