import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from './api';

export function Landing() {
  return (
    <div style={{ maxWidth: 860, margin: '48px auto', padding: 24 }}>
      <h1>ClauseRadar</h1>
      <p className="muted">From contract clauses to actions.</p>
      <p>
        ClauseRadar converts contracts into structured, evidence-backed operational
        obligations — with human verification, deadlines, risk analysis, and audit trail.
      </p>
      <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
        <Link className="btn" to="/workspace">Explore ClauseRadar</Link>
        <Link className="btn secondary" to="/workspace">Create Workspace</Link>
      </div>
      <p className="muted" style={{ marginTop: 16 }}>
        No signup required for evaluation. Deterministic business logic works even when AI is unavailable.
      </p>
    </div>
  );
}

export function Overview() {
  const health = useQuery({ queryKey: ['health'], queryFn: api.health });
  return (
    <div>
      <h1>Overview</h1>
      <p className="muted">Phase 00 shell — domain pages land in later phases.</p>
      <div className="grid">
        <div className="card">
          <h3>API health</h3>
          {health.isPending && <p className="muted">Checking backend…</p>}
          {health.isError && <p>Backend unreachable: {(health.error as Error).message}</p>}
          {health.data && <p><span className="status">{health.data.status}</span> {health.data.service}</p>}
        </div>
        <div className="card">
          <h3>What&apos;s next</h3>
          <p className="muted">Contracts, obligations, deadlines, risk, search, audit, and evidence-grounded Q&amp;A.</p>
        </div>
      </div>
    </div>
  );
}

export function Placeholder({ title }: { title: string }) {
  return (
    <div>
      <h1>{title}</h1>
      <div className="card">
        <p className="muted">This section is scaffolded in Phase 00 and implemented in its dedicated phase.</p>
      </div>
    </div>
  );
}
