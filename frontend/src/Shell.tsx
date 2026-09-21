import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from './auth';
import NotificationBell from './components/NotificationBell';

export default function Shell() {
  const { user, authLoading, logout, workspaces, activeWorkspace, setActiveWorkspaceId, evalMode, resetEvalWorkspace } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  async function handleReset() {
    if (!window.confirm('Reset the evaluation workspace to its seeded state? Your changes will be discarded.')) return;
    await resetEvalWorkspace();
    navigate('/');
    window.location.reload();
  }

  return (
    <div className="shell">
      <aside className="sidebar" aria-label="Primary">
        <div className="brand">
          ClauseRadar
          <small>From contract clauses to actions.</small>
        </div>
        <nav className="nav" aria-label="Sections">
          <NavLink to="/" end>Overview</NavLink>
          <NavLink to="/contracts">Contracts</NavLink>
          <NavLink to="/obligations">Obligations</NavLink>
          <NavLink to="/deadlines">Deadlines</NavLink>
          <NavLink to="/risks">Risk Radar</NavLink>
          <NavLink to="/ask">Ask</NavLink>
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/audit">Audit Log</NavLink>
          <NavLink to="/settings">Settings</NavLink>
          <NavLink to="/architecture">Architecture</NavLink>
        </nav>
        <div className="sidebar-footer">
          {!authLoading && user && workspaces.length > 0 && (
            <label className="field">
              <span>Workspace</span>
              <select
                aria-label="Active workspace"
                value={activeWorkspace?.id ?? ''}
                onChange={(e) => setActiveWorkspaceId(e.target.value || null)}
              >
                {workspaces.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.organization_slug}/{w.slug}
                  </option>
                ))}
              </select>
            </label>
          )}
          {!authLoading && user ? (
            <div className="userbox">
              <span className="muted" title={user.email}>
                {user.display_name || user.email}
              </span>
              <NotificationBell />
              <button className="btn secondary btn-sm" type="button" onClick={handleLogout}>
                Log out
              </button>
            </div>
          ) : (
            !authLoading && (
              <div className="userbox">
                <NavLink className="btn btn-sm" to="/login">Log in</NavLink>
                <NavLink className="btn secondary btn-sm" to="/register">Register</NavLink>
              </div>
            )
          )}
        </div>
      </aside>
      <main className="main">
        {evalMode && (
          <div className="eval-banner" role="status">
            <span>Public evaluation workspace — fictional ACME demo data, real backend.</span>
            <button className="btn secondary btn-sm" type="button" onClick={handleReset}>
              Reset evaluation workspace
            </button>
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
