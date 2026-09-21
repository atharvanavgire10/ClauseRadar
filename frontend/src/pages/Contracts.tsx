import { useState } from 'react';
import type { FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, buildQuery, getErrorMessage } from '../api';
import type { Contract } from '../api';
import { useAuth } from '../auth';
import { EmptyState, ErrorState, Loading, PageHeader, StatusBadge } from '../components';
import { validateContractTitle, validateDateOrder } from '../validation';

const STATUSES = ['DRAFT', 'ACTIVE', 'EXPIRED', 'TERMINATED', 'ARCHIVED'];

export default function Contracts() {
  const { user, activeWorkspace } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: '', counterparty: '', description: '', status: 'DRAFT', start_date: '', end_date: '', renewal_date: '' });
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const query = buildQuery({ workspace: activeWorkspace?.id, search: search || undefined, status: status || undefined });
  const list = useQuery({
    queryKey: ['contracts', 'list', activeWorkspace?.id, search, status],
    queryFn: () => api.contracts(query),
    enabled: Boolean(user && activeWorkspace),
  });

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    const titleErr = validateContractTitle(form.title);
    const dateErr = validateDateOrder(form.start_date, form.end_date);
    if (titleErr || dateErr) {
      setFormError(titleErr ?? dateErr);
      return;
    }
    if (!activeWorkspace) return;
    setSaving(true);
    setFormError(null);
    try {
      const payload: Partial<Contract> = {
        workspace: activeWorkspace.id,
        title: form.title.trim(),
        counterparty: form.counterparty.trim(),
        description: form.description.trim(),
        status: form.status,
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        renewal_date: form.renewal_date || null,
      };
      await api.createContract(payload);
      setForm({ title: '', counterparty: '', description: '', status: 'DRAFT', start_date: '', end_date: '', renewal_date: '' });
      setShowForm(false);
      await queryClient.invalidateQueries({ queryKey: ['contracts'] });
      await queryClient.invalidateQueries({ queryKey: ['audit'] });
    } catch (err) {
      setFormError(getErrorMessage(err, 'Could not create contract.'));
    } finally {
      setSaving(false);
    }
  }

  if (!user) {
    return (<div><PageHeader title="Contracts" subtitle="Log in to manage contracts." /><EmptyState title="Not logged in" hint="Log in to view contracts." action={<Link className="btn" to="/login">Log in</Link>} /></div>);
  }
  if (!activeWorkspace) {
    return (<div><PageHeader title="Contracts" /><EmptyState title="No workspace selected" hint="Create a workspace in Settings first." action={<Link className="btn" to="/settings">Go to Settings</Link>} /></div>);
  }

  return (
    <div>
      <PageHeader
        title="Contracts"
        subtitle={`${activeWorkspace.organization_slug}/${activeWorkspace.slug} — ${list.data?.count ?? '…'} contract(s).`}
        actions={<button className="btn" type="button" onClick={() => setShowForm((v) => !v)}>{showForm ? 'Close' : 'New contract'}</button>}
      />
      {showForm && (
        <form className="card form" onSubmit={onCreate} noValidate>
          <h3 style={{ marginTop: 0 }}>New contract</h3>
          {formError && <p role="alert" className="form-error">{formError}</p>}
          <label className="field"><span>Title *</span><input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} maxLength={300} /></label>
          <div className="form-row">
            <label className="field"><span>Counterparty</span><input value={form.counterparty} onChange={(e) => setForm({ ...form, counterparty: e.target.value })} /></label>
            <label className="field"><span>Status</span>
              <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
          </div>
          <label className="field"><span>Description</span><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} /></label>
          <div className="form-row">
            <label className="field"><span>Start date</span><input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></label>
            <label className="field"><span>End date</span><input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></label>
            <label className="field"><span>Renewal date</span><input type="date" value={form.renewal_date} onChange={(e) => setForm({ ...form, renewal_date: e.target.value })} /></label>
          </div>
          <button className="btn" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Create contract'}</button>
        </form>
      )}
      <div className="toolbar" role="search">
        <input type="search" placeholder="Search title, counterparty…" aria-label="Search contracts" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select aria-label="Filter by status" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      {list.isPending && <Loading label="Loading contracts…" />}
      {list.isError && <ErrorState error={list.error} onRetry={() => list.refetch()} />}
      {list.data && list.data.results.length === 0 && (
        <EmptyState title="No contracts found" hint="Try a different search, or create your first contract." />
      )}
      {list.data && list.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th scope="col">Title</th><th scope="col">Counterparty</th><th scope="col">Status</th><th scope="col">Renewal</th></tr></thead>
            <tbody>
              {list.data.results.map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/contracts/${c.id}`}>{c.title}</Link></td>
                  <td>{c.counterparty || '—'}</td>
                  <td><StatusBadge value={c.status} /></td>
                  <td>{c.renewal_date ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
