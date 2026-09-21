import { useState } from 'react';
import type { FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, buildQuery, getErrorMessage } from '../api';
import { EmptyState } from '../components';

export function CommentsThread({ obligationId }: { obligationId: string }) {
  const queryClient = useQueryClient();
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const list = useQuery({
    queryKey: ['comments', obligationId],
    queryFn: () => api.comments(buildQuery({ obligation: obligationId, page_size: 50 })),
  });

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setBusy(true);
    try {
      await api.createComment({ obligation: obligationId, body: body.trim() });
      setBody('');
      await queryClient.invalidateQueries({ queryKey: ['comments', obligationId] });
    } catch {
      /* shown via list error on refetch */
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {list.data && list.data.results.length === 0 && <p className="muted" style={{ fontSize: 13 }}>No comments yet.</p>}
      {list.data?.results.map((c) => (
        <p key={c.id} style={{ fontSize: 13 }}>
          <strong>{c.author_email ?? '—'}</strong>{' '}
          <span className="muted">{new Date(c.created_at).toLocaleString()}</span><br />{c.body}
        </p>
      ))}
      <form onSubmit={onAdd} className="toolbar" style={{ marginTop: 8 }}>
        <input aria-label="Add a comment" placeholder="Add a comment…" value={body} onChange={(e) => setBody(e.target.value)} />
        <button className="btn secondary btn-sm" type="submit" disabled={busy || !body.trim()}>{busy ? 'Posting…' : 'Post'}</button>
      </form>
    </div>
  );
}

export function EvidencePanel({ obligationId }: { obligationId: string }) {
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const list = useQuery({
    queryKey: ['evidence', obligationId],
    queryFn: () => api.evidenceList(buildQuery({ obligation: obligationId, page_size: 50 })),
  });

  async function onFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setNote(null);
    try {
      await api.uploadEvidence(obligationId, file);
      setNote('Evidence attached.');
      await queryClient.invalidateQueries({ queryKey: ['evidence', obligationId] });
      await queryClient.invalidateQueries({ queryKey: ['risks'] });
    } catch (err) {
      setNote(getErrorMessage(err, 'Upload failed.'));
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: string) {
    setBusy(true);
    try {
      await api.deleteEvidence(id);
      await queryClient.invalidateQueries({ queryKey: ['evidence', obligationId] });
    } catch (err) {
      setNote(getErrorMessage(err, 'Delete failed.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <label className="field">
        <span>Attach evidence (PDF, DOCX, PNG, JPG)</span>
        <input type="file" accept=".pdf,.docx,.png,.jpg,.jpeg" disabled={busy}
          onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ''; }} />
      </label>
      {note && <p className="muted" role="status" style={{ fontSize: 13 }}>{note}</p>}
      {list.data && list.data.results.length === 0 && <p className="muted" style={{ fontSize: 13 }}>No evidence attached.</p>}
      {list.data?.results.map((ev) => (
        <p key={ev.id} style={{ fontSize: 13 }}>
          <strong>{ev.original_filename}</strong>{' '}
          <span className="muted">{(ev.size_bytes / 1024).toFixed(1)} KB · {ev.uploaded_by_email ?? '—'}</span>
          {ev.note && <span> · {ev.note}</span>}{' '}
          <button className="btn secondary btn-sm" type="button" disabled={busy} onClick={() => onDelete(ev.id)}>Remove</button>
        </p>
      ))}
    </div>
  );
}

export function TasksSection({ contractId }: { contractId: string }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const list = useQuery({
    queryKey: ['tasks', contractId],
    queryFn: () => api.tasks(buildQuery({ contract: contractId, page_size: 50 })),
  });

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setBusy(true);
    try {
      await api.createTask({ contract: contractId, title: title.trim() });
      setTitle('');
      await queryClient.invalidateQueries({ queryKey: ['tasks', contractId] });
    } finally {
      setBusy(false);
    }
  }

  async function onToggle(id: string, done: boolean) {
    await api.updateTask(id, { status: done ? 'OPEN' : 'DONE' });
    await queryClient.invalidateQueries({ queryKey: ['tasks', contractId] });
  }

  return (
    <section aria-label="Tasks">
      <h2>Tasks</h2>
      {list.data && list.data.results.length === 0 && (
        <EmptyState title="No tasks" hint="Track operational follow-ups linked to this contract." />
      )}
      {list.data?.results.map((t) => (
        <p key={t.id} style={{ fontSize: 14 }}>
          <input type="checkbox" checked={t.status === 'DONE'} onChange={() => onToggle(t.id, t.status === 'DONE')}
            aria-label={`Mark ${t.title} ${t.status === 'DONE' ? 'open' : 'done'}`} />{' '}
          <span style={{ textDecoration: t.status === 'DONE' ? 'line-through' : 'none' }}>{t.title}</span>{' '}
          <span className="muted" style={{ fontSize: 12 }}>{t.status} {t.assignee_email ? `· ${t.assignee_email}` : ''}</span>
        </p>
      ))}
      <form onSubmit={onAdd} className="toolbar">
        <input aria-label="New task title" placeholder="New task, e.g. Chase insurance certificate…" value={title} onChange={(e) => setTitle(e.target.value)} />
        <button className="btn secondary" type="submit" disabled={busy || !title.trim()}>{busy ? 'Adding…' : 'Add task'}</button>
      </form>
    </section>
  );
}
