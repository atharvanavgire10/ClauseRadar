import { useState } from 'react';
import type { FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, getErrorMessage } from '../api';
import { useAuth } from '../auth';
import { EmptyState, PageHeader } from '../components';

function AIStatusCard() {
  const status = useQuery({ queryKey: ['ai-status'], queryFn: api.aiStatus });
  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>AI assistance</h3>
      {status.isPending && <p className="muted">Checking…</p>}
      {status.isError && <p className="muted">Status unavailable.</p>}
      {status.data && (
        <>
          <p>
            <span className={`badge ${status.data.configured ? 'badge-ok' : 'badge-neutral'}`}>
              {status.data.configured ? `ENABLED · ${status.data.provider}` : 'DISABLED'}
            </span>
          </p>
          <p className="muted" style={{ fontSize: 13 }}>{status.data.note}</p>
        </>
      )}
    </div>
  );
}

function NotificationPrefs() {
  const prefs = useQuery({ queryKey: ['notification-prefs'], queryFn: api.notificationPrefs });
  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Notification preferences</h3>
      {prefs.isPending && <p className="muted">Loading…</p>}
      {prefs.data && prefs.data.length === 0 && <p className="muted">No preference kinds.</p>}
      {prefs.data && prefs.data.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th scope="col">Event</th><th scope="col">In-app</th><th scope="col">Email</th></tr></thead>
            <tbody>
              {prefs.data.map((p) => (
                <tr key={p.kind}><td><code>{p.kind}</code></td><td>{p.in_app ? 'on' : 'off'}</td><td>{p.email ? 'on' : 'off'}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="muted" style={{ fontSize: 12 }}>Preferences are enforced server-side for both in-app delivery and email.</p>
    </div>
  );
}

export default function Settings() {
  const { user, workspaces, activeWorkspace, refreshWorkspaces } = useAuth();
  const queryClient = useQueryClient();
  const [orgName, setOrgName] = useState('');
  const [wsName, setWsName] = useState('');
  const [wsOrg, setWsOrg] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [orgs, setOrgs] = useState<{ id: string; name: string; slug: string }[]>([]);

  async function loadOrgs() {
    try {
      const page = await api.organizations();
      setOrgs(page.results);
      if (!wsOrg && page.results[0]) setWsOrg(page.results[0].id);
    } catch {
      /* shown inline on submit */
    }
  }

  if (!user) {
    return (<div><PageHeader title="Settings" subtitle="Log in to manage organizations and workspaces." /><EmptyState title="Not logged in" /></div>);
  }

  async function onCreateOrg(e: FormEvent) {
    e.preventDefault();
    if (!orgName.trim()) {
      setMessage('Organization name is required.');
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await api.createOrganization({ name: orgName.trim() });
      setOrgName('');
      await refreshWorkspaces();
      await loadOrgs();
      await queryClient.invalidateQueries();
      setMessage('Organization created.');
    } catch (err) {
      setMessage(getErrorMessage(err, 'Could not create organization.'));
    } finally {
      setBusy(false);
    }
  }

  async function onCreateWorkspace(e: FormEvent) {
    e.preventDefault();
    if (!wsName.trim() || !wsOrg) {
      setMessage('Workspace name and organization are required.');
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await api.createWorkspace({ organization: wsOrg, name: wsName.trim() });
      setWsName('');
      await refreshWorkspaces();
      await queryClient.invalidateQueries();
      setMessage('Workspace created.');
    } catch (err) {
      setMessage(getErrorMessage(err, 'Could not create workspace.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title="Settings" subtitle={`Signed in as ${user.email}. Manage organizations and workspaces.`} />
      {message && <p className="muted" role="status">{message}</p>}
      <AIStatusCard />
      <NotificationPrefs />
      <div className="grid">
        <form className="card form" onSubmit={onCreateOrg} onFocus={loadOrgs}>
          <h3 style={{ marginTop: 0 }}>New organization</h3>
          <label className="field"><span>Name</span><input value={orgName} onChange={(e) => setOrgName(e.target.value)} placeholder="ACME Industries" /></label>
          <button className="btn" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Create organization'}</button>
        </form>
        <form className="card form" onSubmit={onCreateWorkspace} onFocus={loadOrgs}>
          <h3 style={{ marginTop: 0 }}>New workspace</h3>
          <label className="field"><span>Organization</span>
            <select value={wsOrg} onChange={(e) => setWsOrg(e.target.value)} onFocus={loadOrgs}>
              <option value="">Select…</option>
              {orgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
          </label>
          <label className="field"><span>Name</span><input value={wsName} onChange={(e) => setWsName(e.target.value)} placeholder="Legal" /></label>
          <button className="btn" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Create workspace'}</button>
        </form>
      </div>
      <h2>Your workspaces</h2>
      {workspaces.length === 0 && <EmptyState title="No workspaces" hint="Create an organization first, then a workspace inside it." />}
      {workspaces.length > 0 && (
        <div className="table-wrap"><table>
          <thead><tr><th scope="col">Workspace</th><th scope="col">Type</th><th scope="col">Role</th></tr></thead>
          <tbody>{workspaces.map((w) => (
            <tr key={w.id} className={activeWorkspace?.id === w.id ? 'row-active' : ''}>
              <td>{w.organization_slug}/{w.slug}</td><td>{w.workspace_type}</td><td>{w.role ?? '—'}</td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
    </div>
  );
}
