import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, buildQuery } from '../api';
import { useAuth } from '../auth';
import { EmptyState, ErrorState, Loading, PageHeader, StatusBadge } from '../components';

export default function Overview() {
  const { user, activeWorkspace } = useAuth();
  const wsId = activeWorkspace?.id;

  const contracts = useQuery({
    queryKey: ['contracts', 'overview', wsId],
    queryFn: () => api.contracts(buildQuery({ workspace: wsId, page_size: 5 })),
    enabled: Boolean(user && wsId),
  });
  const audit = useQuery({
    queryKey: ['audit', 'overview', wsId],
    queryFn: () => api.audit(buildQuery({ workspace: wsId, page_size: 8 })),
    enabled: Boolean(user && wsId),
  });
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, staleTime: 60_000 });

  if (!user) {
    return (
      <div>
        <PageHeader title="Overview" subtitle="Log in to see your workspace at a glance." />
        <div className="card">
          <p className="muted">You are not logged in. ClauseRadar workspaces require authentication; the public evaluation workspace arrives in Phase 17.</p>
          <div className="cta-row"><Link className="btn" to="/login">Log in</Link><Link className="btn secondary" to="/register">Register</Link></div>
        </div>
      </div>
    );
  }

  if (!activeWorkspace) {
    return (
      <div>
        <PageHeader title="Overview" subtitle="Create an organization and workspace to begin." />
        <EmptyState title="No workspace yet" hint="Head to Settings to create your first organization and workspace." action={<Link className="btn" to="/settings">Go to Settings</Link>} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title={`${activeWorkspace.organization_slug}/${activeWorkspace.slug}`}
        subtitle={activeWorkspace.description || 'Workspace overview — live data from the ClauseRadar API.'}
        actions={<Link className="btn secondary" to="/contracts">View contracts</Link>}
      />
      <div className="grid">
        <div className="card">
          <h3>Backend</h3>
          {health.isPending ? <p className="muted">Checking…</p>
            : health.isError ? <p>Unreachable</p>
            : <p><span className="status">{health.data.status}</span> {health.data.service}</p>}
        </div>
        <div className="card">
          <h3>Contracts</h3>
          {contracts.isPending ? <p className="muted">Loading…</p>
            : contracts.isError ? <p className="muted">Unable to load.</p>
            : <p className="bignum">{contracts.data.count}</p>}
        </div>
        <div className="card">
          <h3>Recent activity</h3>
          {audit.isPending ? <p className="muted">Loading…</p>
            : audit.isError ? <p className="muted">Unable to load.</p>
            : <p className="bignum">{audit.data.count}</p>}
        </div>
      </div>

      <h2>Latest contracts</h2>
      {contracts.isPending && <Loading label="Loading contracts…" />}
      {contracts.isError && <ErrorState error={contracts.error} onRetry={() => contracts.refetch()} />}
      {contracts.data && contracts.data.results.length === 0 && (
        <EmptyState title="No contracts yet" hint="Create your first contract to start extracting obligations." action={<Link className="btn" to="/contracts">Go to Contracts</Link>} />
      )}
      {contracts.data && contracts.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th scope="col">Title</th><th scope="col">Counterparty</th><th scope="col">Status</th></tr></thead>
            <tbody>
              {contracts.data.results.map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/contracts/${c.id}`}>{c.title}</Link></td>
                  <td>{c.counterparty || '—'}</td>
                  <td><StatusBadge value={c.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2>Recent audit events</h2>
      {audit.isPending && <Loading label="Loading audit trail…" />}
      {audit.isError && <ErrorState error={audit.error} onRetry={() => audit.refetch()} />}
      {audit.data && audit.data.results.length === 0 && <EmptyState title="No audit events" hint="Actions you take will appear here." />}
      {audit.data && audit.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th scope="col">Action</th><th scope="col">Entity</th><th scope="col">When</th></tr></thead>
            <tbody>
              {audit.data.results.map((e) => (
                <tr key={e.id}>
                  <td><code>{e.action}</code></td>
                  <td>{e.entity_type}:{e.entity_id.slice(0, 8)}…</td>
                  <td>{new Date(e.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
