import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../api/client.js';

export default function AnalyticsPage() {
  const [overview, setOverview] = useState(null);
  const [branch, setBranch] = useState(null);

  useEffect(() => {
    api.analyticsOverview().then(setOverview).catch(() => {});
    api.analyticsByBranch().then(setBranch).catch(() => {});
  }, []);

  const branchChartData = branch
    ? Object.entries(branch).map(([name, stats]) => ({
        name,
        averageSgpa: stats.average_sgpa ?? 0,
      }))
    : [];

  return (
    <div>
      <h2>Analytics</h2>

      {overview && (
        <div style={{ display: 'flex', gap: 24, marginBottom: 24 }}>
          <Stat label="Students processed" value={overview.count} />
          <Stat label="Average SGPA" value={overview.average_sgpa} />
          <Stat label="Pass rate" value={`${overview.pass_rate ?? '-'}%`} />
        </div>
      )}

      <h3>Branch Performance</h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={branchChartData}>
          <XAxis dataKey="name" />
          <YAxis domain={[0, 10]} />
          <Tooltip />
          <Bar dataKey="averageSgpa" fill="#3b82f6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div style={{ border: '1px solid #ddd', padding: 12, borderRadius: 8 }}>
      <div style={{ fontSize: 12, color: '#666' }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 600 }}>{value ?? '-'}</div>
    </div>
  );
}
