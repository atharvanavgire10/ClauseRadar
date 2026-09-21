import { useState } from 'react';
import type { FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, buildQuery, getErrorMessage } from '../api';
import type { AuditEvent, Obligation } from '../api';
import { splitHighlight } from '../highlight';
import { EmptyState, ErrorState, Loading, StatusBadge } from '../components';
import { CommentsThread, EvidencePanel } from './OperationsPanel';

export function ObligationCard({ ob, onChanged }: { ob: Obligation; onChanged: () => void }) {
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [title, setTitle] = useState(ob.title);
  const [actor, setActor] = useState(ob.actor);
  const [priority, setPriority] = useState(ob.priority ?? 'MEDIUM');
  const [notes, setNotes] = useState(ob.notes ?? '');
  const [note, setNote] = useState<string | null>(null);

  const members = useQuery({
    queryKey: ['members', ob.workspace],
    queryFn: () => api.workspaceMembers(ob.workspace),
  });

  const history = useQuery({
    queryKey: ['audit', 'obligation', ob.id],
    queryFn: () => api.audit(buildQuery({ entity_type: 'obligation', entity_id: ob.id, page_size: 50 })),
    enabled: showHistory,
  });
  const [before, hit, after] = splitHighlight(ob.source_text, ob.action);

  async function run(fn: () => Promise<Obligation>, okMsg: string) {
    setBusy(true);
    setNote(null);
    try {
      await fn();
      setNote(okMsg);
      await queryClient.invalidateQueries({ queryKey: ['obligations'] });
      onChanged();
    } catch (err) {
      setNote(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function onSaveEdit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setNote('Title is required.');
      return;
    }
    await run(() => api.updateObligation(ob.id, { title: title.trim(), actor }), 'Saved.');
    setEditing(false);
  }

  return (
    <article className="card">
      <div className="row-actions" style={{ justifyContent: 'space-between' }}>
        <span className="badge badge-neutral">{ob.obligation_type}</span>
        <StatusBadge value={ob.status} />
      </div>
      {editing ? (
        <form className="form" onSubmit={onSaveEdit} style={{ marginTop: 8 }}>
          <label className="field"><span>Title</span><input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={300} /></label>
          <label className="field"><span>Actor</span><input value={actor} onChange={(e) => setActor(e.target.value)} maxLength={120} /></label>
          <div className="row-actions">
            <button className="btn btn-sm" type="submit" disabled={busy}>Save</button>
            <button className="btn secondary btn-sm" type="button" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </form>
      ) : (
        <h4 style={{ marginBottom: 4 }}>{ob.title}</h4>
      )}
      <p className="muted" style={{ fontSize: 13, margin: '4px 0' }}>
        {ob.actor && <span><strong>Actor:</strong> {ob.actor} · </span>}
        <strong>Action:</strong> {ob.action || '—'} · <strong>Frequency:</strong> {ob.frequency}
        {ob.evidence_required && <span> · <strong>Evidence:</strong> {ob.evidence_required}</span>}
      </p>
      <p className="muted" style={{ fontSize: 13, margin: '4px 0' }}>
        <strong>Owner:</strong> {ob.owner_email ?? 'unassigned'} · <strong>Priority:</strong> {ob.priority ?? 'MEDIUM'}
        {ob.notes && <span> · <strong>Notes:</strong> {ob.notes}</span>}
      </p>
      <div className="toolbar" style={{ marginBottom: 4 }}>
        <select aria-label="Assign owner" value={ob.owner ?? ''} disabled={busy}
          onChange={(e) => run(() => api.assignObligation(ob.id, members.data?.find((m) => m.user === e.target.value)?.user_email ?? ''), 'Owner updated.')}>
          <option value="">Unassigned</option>
          {members.data?.map((m) => <option key={m.user} value={m.user}>{m.user_email} ({m.role})</option>)}
        </select>
        <select aria-label="Priority" value={priority} disabled={busy}
          onChange={(e) => { setPriority(e.target.value); run(() => api.updateObligation(ob.id, { priority: e.target.value }), 'Priority updated.'); }}>
          {['LOW','MEDIUM','HIGH','URGENT'].map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>
      <details>
        <summary>Notes</summary>
        <form className="form" style={{ marginTop: 8 }} onSubmit={(e) => { e.preventDefault(); run(() => api.updateObligation(ob.id, { notes }), 'Notes saved.'); }}>
          <label className="field"><span>Reviewer notes</span><textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
          <button className="btn secondary btn-sm" type="submit" disabled={busy}>Save notes</button>
        </form>
      </details>
      <details>
        <summary>Comments &amp; evidence</summary>
        <h5>Comments</h5>
        <CommentsThread obligationId={ob.id} />
        <h5>Evidence</h5>
        <EvidencePanel obligationId={ob.id} />
      </details>
      <details>
        <summary>Source evidence (p{ob.page_number}, {Math.round(ob.confidence * 100)}% via {ob.extraction_method})</summary>
        <blockquote className="evidence">
          {hit ? <>{before}<mark>{hit}</mark>{after}</> : ob.source_text}
        </blockquote>
        {ob.reviewer_email && <p className="muted" style={{ fontSize: 12 }}>Reviewed by {ob.reviewer_email} at {ob.reviewed_at ? new Date(ob.reviewed_at).toLocaleString() : '—'}</p>}
      </details>
      <details onToggle={(e) => setShowHistory((e.target as HTMLDetailsElement).open)}>
        <summary>Extraction &amp; review history</summary>
        {!showHistory && <p className="muted" style={{ fontSize: 13 }}>Open to load the audit trail for this obligation.</p>}
        {history.isPending && showHistory && <p className="muted">Loading history…</p>}
        {history.isError && <p className="form-error">{getErrorMessage(history.error)}</p>}
        {history.data && history.data.results.length === 0 && <p className="muted">No history events.</p>}
        {history.data && history.data.results.length > 0 && (
          <ul className="history">
            {history.data.results.map((e: AuditEvent) => (
              <li key={e.id}><code>{e.action}</code> <span className="muted">{e.actor_email ?? 'system'} · {new Date(e.created_at).toLocaleString()}</span></li>
            ))}
          </ul>
        )}
      </details>
      {ob.status === 'NEEDS_REVIEW' && !editing && (
        <div className="row-actions" style={{ marginTop: 8 }}>
          <button className="btn btn-sm" type="button" disabled={busy} onClick={() => run(() => api.confirmObligation(ob.id), 'Confirmed.')}>Approve</button>
          <button className="btn secondary btn-sm" type="button" disabled={busy} onClick={() => { const r = window.prompt('Rejection reason (optional):', ''); if (r !== null) run(() => api.rejectObligation(ob.id, r), 'Rejected.'); }}>Reject</button>
          <button className="btn secondary btn-sm" type="button" onClick={() => setEditing(true)}>Edit</button>
        </div>
      )}
      {ob.status === 'CONFIRMED' && (
        <div className="row-actions" style={{ marginTop: 8 }}>
          <button className="btn secondary btn-sm" type="button" disabled={busy} onClick={() => run(() => api.activateObligation(ob.id), 'Activated.')}>Activate</button>
        </div>
      )}
      {ob.status === 'ACTIVE' && (
        <div className="row-actions" style={{ marginTop: 8 }}>
          <button className="btn secondary btn-sm" type="button" disabled={busy} onClick={() => run(() => api.startObligation(ob.id), 'In progress.')}>Start progress</button>
          <button className="btn secondary btn-sm" type="button" disabled={busy} onClick={() => run(() => api.completeObligation(ob.id), 'Completed.')}>Complete</button>
          <button className="btn secondary btn-sm" type="button" disabled={busy} onClick={() => { const r = window.prompt('Waiver reason:', ''); if (r !== null) run(() => api.waiveObligation(ob.id, r), 'Waived.'); }}>Waive</button>
        </div>
      )}
      {ob.status === 'IN_PROGRESS' && (
        <div className="row-actions" style={{ marginTop: 8 }}>
          <button className="btn secondary btn-sm" type="button" disabled={busy} onClick={() => run(() => api.completeObligation(ob.id), 'Completed.')}>Complete</button>
          <button className="btn secondary btn-sm" type="button" disabled={busy} onClick={() => { const r = window.prompt('Waiver reason:', ''); if (r !== null) run(() => api.waiveObligation(ob.id, r), 'Waived.'); }}>Waive</button>
        </div>
      )}
      {(ob.status === 'COMPLETED' || ob.status === 'WAIVED') && (
        <div className="row-actions" style={{ marginTop: 8 }}>
          <button className="btn secondary btn-sm" type="button" disabled={busy} onClick={() => run(() => api.reopenObligation(ob.id), 'Reopened.')}>Reopen</button>
        </div>
      )}
      {note && <p className="muted" role="status" style={{ fontSize: 13 }}>{note}</p>}
    </article>
  );
}

export default function ObligationsSection({ contractId }: { contractId: string }) {
  const [statusFilter, setStatusFilter] = useState('');
  const query = buildQuery({ contract: contractId, status: statusFilter || undefined, page_size: 100 });
  const list = useQuery({
    queryKey: ['obligations', contractId, statusFilter],
    queryFn: () => api.obligations(query),
  });

  return (
    <section aria-label="Obligations">
      <h2>Obligations</h2>
      <div className="toolbar">
        <select aria-label="Filter by status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          {['NEEDS_REVIEW','CONFIRMED','REJECTED','ACTIVE','IN_PROGRESS','COMPLETED','WAIVED'].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      {list.isPending && <Loading label="Loading obligations…" />}
      {list.isError && <ErrorState error={list.error} onRetry={() => list.refetch()} />}
      {list.data && list.data.results.length === 0 && (
        <EmptyState title="No obligations found" hint="Extracted obligations appear here as NEEDS_REVIEW for human verification." />
      )}
      {list.data?.results.map((ob) => <ObligationCard key={ob.id} ob={ob} onChanged={() => list.refetch()} />)}
    </section>
  );
}
