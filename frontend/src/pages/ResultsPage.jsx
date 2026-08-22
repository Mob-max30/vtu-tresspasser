import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function ResultsPage() {
  const [results, setResults] = useState([]);

  useEffect(() => {
    api.listResults().then(setResults).catch(() => {});
  }, []);

  return (
    <div>
      <h2>Results ({results.length})</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th align="left">USN</th>
            <th align="left">Branch</th>
            <th align="left">Cycle</th>
            <th align="left">SGPA</th>
            <th align="left">Status</th>
            <th align="left">Source</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <tr key={r.usn}>
              <td>{r.usn}</td>
              <td>{r.branch}</td>
              <td>{r.cycle}</td>
              <td>{r.sgpa}</td>
              <td>{r.status}</td>
              <td>{r.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
