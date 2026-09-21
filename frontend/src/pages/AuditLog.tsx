import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, buildQuery } from '../api';
import { useAuth } from '../auth';
import { EmptyState, ErrorState, Loading, PageHeader } from '../components';

export default function AuditLog() {
  const { user, activeWorkspace } = useAuth();
  const [action, setAction] = useState('');
  const query = buildQuery({ workspace: activeWorkspace?.id, action: action || undefined, page_size: 50 });
  const log = useQuery({
    queryKey: ['audit', 'log', activeWorkspace?.id, action],
    queryFn: () => api.audit(query),
    enabled: Boolean(user && activeWorkspace),
  });

  if (!user) return (<div><PageHeader title="Audit Log" /><EmptyState title="Not logged in" action={<Link className="btn" to="/login">Log in</Link>} /></div>);
  if (!activeWorkspace) return (<div><PageHeader title="Audit Log" /><EmptyState title="No workspace selected" /></div>);

  return (
    <div>
      <PageHeader title="Audit Log" subtitle={`Append-only trail for ${activeWorkspace.organization_slug}/${activeWorkspace.slug}.`} />
      <div className="toolbar">
        <input aria-label="Filter by action" placeholder="Filter by action, e.g. contract.created" value={action} onChange={(e) => setAction(e.target.value)} />
      </div>
      {log.isPending && <Loading label="Loading audit trail…" />}
      {log.isError && <ErrorState error={log.error} onRetry={() => log.refetch()} />}
      {log.data && log.data.results.length === 0 && <EmptyState title="No audit events" hint="Every create, update, and review action is recorded here." />}
      {log.data && log.data.results.length > 0 && (
        <div className="table-wrap"><table>
          <thead><tr><th scope="col">When</th><th scope="col">Action</th><th scope="col">Entity</th><th scope="col">Actor</th></tr></thead>
          <tbody>{log.data.results.map((e) => (
            <tr key={e.id}>
              <td>{new Date(e.created_at).toLocaleString()}</td>
              <td><code>{e.action}</code></td>
              <td>{e.entity_type}:{e.entity_id.slice(0, 8)}…</td>
              <td>{e.actor_email ?? '—'}</td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
    </div>
  );
}
