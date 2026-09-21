import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, buildQuery, getErrorMessage } from '../api';
import { useAuth } from '../auth';
import { EmptyState, ErrorState, Loading, PageHeader, StatusBadge } from '../components';

const STATUSES = ['OVERDUE', 'DUE_SOON', 'UPCOMING', 'COMPLETED', 'WAIVED'];

export default function Deadlines() {
  const { user, activeWorkspace } = useAuth();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const query = buildQuery({ workspace: activeWorkspace?.id, status: statusFilter || undefined, page_size: 100 });
  const list = useQuery({
    queryKey: ['deadlines', activeWorkspace?.id, statusFilter],
    queryFn: () => api.deadlines(query),
    enabled: Boolean(user && activeWorkspace),
  });

  async function run(id: string, fn: (id: string) => Promise<unknown>, msg: string) {
    setBusyId(id);
    setNote(null);
    try {
      await fn(id);
      setNote(msg);
      await queryClient.invalidateQueries({ queryKey: ['deadlines'] });
    } catch (err) {
      setNote(getErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  if (!user) return (<div><PageHeader title="Deadlines" /><EmptyState title="Not logged in" action={<Link className="btn" to="/login">Log in</Link>} /></div>);
  if (!activeWorkspace) return (<div><PageHeader title="Deadlines" /><EmptyState title="No workspace selected" /></div>);

  return (
    <div>
      <PageHeader
        title="Deadlines"
        subtitle="Deterministic, timezone-aware due dates computed from renewal dates, anchors, and explicit dates — never guessed."
      />
      {note && <p className="muted" role="status">{note}</p>}
      <div className="toolbar" role="search">
        <select aria-label="Filter by status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      {list.isPending && <Loading label="Loading deadlines…" />}
      {list.isError && <ErrorState error={list.error} onRetry={() => list.refetch()} />}
      {list.data && list.data.results.length === 0 && (
        <EmptyState title="No deadlines" hint="Set renewal or end dates on contracts, or state explicit dates in obligations, to generate deadlines." />
      )}
      {list.data && list.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th scope="col">Deadline</th><th scope="col">Due</th><th scope="col">Status</th><th scope="col">Rule</th><th scope="col">Actions</th></tr></thead>
            <tbody>
              {list.data.results.map((d) => (
                <tr key={d.id}>
                  <td><Link to={`/contracts/${d.contract}`}>{d.title}</Link><div className="muted" style={{ fontSize: 12 }}>{d.kind}</div></td>
                  <td>{d.due_date}</td>
                  <td><StatusBadge value={d.status} /></td>
                  <td className="muted" style={{ fontSize: 12 }}>{d.rule || '—'}</td>
                  <td>
                    <div className="row-actions">
                      {!d.completed && <button className="btn secondary btn-sm" type="button" disabled={busyId === d.id} onClick={() => run(d.id, api.completeDeadline, 'Marked completed.')}>Complete</button>}
                      {d.completed && <button className="btn secondary btn-sm" type="button" disabled={busyId === d.id} onClick={() => run(d.id, api.reopenDeadline, 'Reopened.')}>Reopen</button>}
                      {!d.waived && !d.completed && <button className="btn secondary btn-sm" type="button" disabled={busyId === d.id} onClick={() => run(d.id, api.waiveDeadline, 'Waived.')}>Waive</button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
