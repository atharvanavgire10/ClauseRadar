import { NavLink, Outlet } from 'react-router-dom';

export default function Shell() {
  return (
    <div className="shell">
      <aside className="sidebar" aria-label="Primary">
        <div className="brand">
          ClauseRadar
          <small>From contract clauses to actions.</small>
        </div>
        <nav className="nav">
          <NavLink to="/" end>Overview</NavLink>
          <NavLink to="/contracts">Contracts</NavLink>
          <NavLink to="/obligations">Obligations</NavLink>
          <NavLink to="/deadlines">Deadlines</NavLink>
          <NavLink to="/risks">Risk Radar</NavLink>
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/audit">Audit Log</NavLink>
          <NavLink to="/settings">Settings</NavLink>
          <NavLink to="/architecture">Architecture</NavLink>
        </nav>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
