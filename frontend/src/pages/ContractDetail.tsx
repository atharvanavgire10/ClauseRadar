import { useState } from 'react';
import type { FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { api, getErrorMessage } from '../api';
import { useAuth } from '../auth';
import { EmptyState, ErrorState, Loading, PageHeader, StatusBadge } from '../components';
import ClausesSection from '../components/ClausesSection';
import DocumentsSection from '../components/DocumentsSection';
import ObligationsSection from '../components/ObligationsSection';
import { TasksSection } from '../components/OperationsPanel';

const STATUSES = ['DRAFT', 'ACTIVE', 'EXPIRED', 'TERMINATED', 'ARCHIVED'];

export default function ContractDetail() {
  const { id = '' } = useParams();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const detail = useQuery({
    queryKey: ['contracts', 'detail', id],
    queryFn: () => api.contract(id),
    enabled: Boolean(user && id),
  });

  const relatedAudit = useQuery({
    queryKey: ['audit', 'contract', id],
    queryFn: () => api.audit(`?search=${id.slice(0, 8)}`),
    enabled: Boolean(user && id && detail.data),
  });

  async function onStatusChange(e: FormEvent) {
    e.preventDefault();
    if (!status) return;
    setSaving(true);
    setMessage(null);
    try {
      await api.updateContract(id, { status });
      setMessage(`Status updated to ${status}.`);
      await queryClient.invalidateQueries({ queryKey: ['contracts'] });
      await queryClient.invalidateQueries({ queryKey: ['audit'] });
    } catch (err) {
      setMessage(getErrorMessage(err, 'Could not update status.'));
    } finally {
      setSaving(false);
    }
  }

  if (!user) return (<div><PageHeader title="Contract" /><EmptyState title="Not logged in" action={<Link className="btn" to="/login">Log in</Link>} /></div>);
  if (detail.isPending) return (<div><PageHeader title="Contract" /><Loading label="Loading contract…" /></div>);
  if (detail.isError) return (<div><PageHeader title="Contract" /><ErrorState error={detail.error} onRetry={() => detail.refetch()} /></div>);

  const c = detail.data;
  return (
    <div>
      <PageHeader
        title={c.title}
        subtitle={`${c.workspace_slug} · counterparty: ${c.counterparty || '—'}`}
        actions={<Link className="btn secondary" to="/contracts">Back to contracts</Link>}
      />
      <div className="grid">
        <div className="card">
          <h3>Details</h3>
          <dl className="dl">
            <dt>Status</dt><dd><StatusBadge value={c.status} /></dd>
            <dt>Counterparty</dt><dd>{c.counterparty || '—'}</dd>
            <dt>Start</dt><dd>{c.start_date ?? '—'}</dd>
            <dt>End</dt><dd>{c.end_date ?? '—'}</dd>
            <dt>Renewal</dt><dd>{c.renewal_date ?? '—'}</dd>
          </dl>
          {c.description && <p className="muted">{c.description}</p>}
        </div>
        <div className="card">
          <h3>Change status</h3>
          <form onSubmit={onStatusChange} className="form">
            <label className="field"><span>New status</span>
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">Select…</option>
                {STATUSES.filter((s) => s !== c.status).map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
            <button className="btn" type="submit" disabled={saving || !status}>{saving ? 'Saving…' : 'Update status'}</button>
            {message && <p className="muted" role="status">{message}</p>}
          </form>
        </div>
      </div>
      <DocumentsSection contractId={c.id} />
      <ClausesSection contractId={c.id} onViewSource={() => {
        document.querySelector('section[aria-label="Documents"]')?.scrollIntoView({ behavior: 'smooth' });
      }} />
      <ObligationsSection contractId={c.id} />
      <TasksSection contractId={c.id} />
      <h2>Related audit</h2>
      {relatedAudit.isPending && <Loading label="Loading related audit…" />}
      {relatedAudit.isError && <p className="muted">Unable to load related audit.</p>}
      {relatedAudit.data && relatedAudit.data.results.length === 0 && <EmptyState title="No related events" hint="Status changes and uploads will appear here." />}
      {relatedAudit.data && relatedAudit.data.results.length > 0 && (
        <div className="table-wrap"><table>
          <thead><tr><th scope="col">Action</th><th scope="col">When</th></tr></thead>
          <tbody>{relatedAudit.data.results.slice(0, 10).map((e) => (
            <tr key={e.id}><td><code>{e.action}</code></td><td>{new Date(e.created_at).toLocaleString()}</td></tr>
          ))}</tbody>
        </table></div>
      )}
    </div>
  );
}
