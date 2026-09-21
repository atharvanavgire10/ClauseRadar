import { Link } from 'react-router-dom';

export default function Landing() {
  return (
    <div className="landing">
      <p className="eyebrow">Contract obligation &amp; risk management</p>
      <h1>ClauseRadar</h1>
      <p className="lede">From contract clauses to actions.</p>
      <p className="muted" style={{ maxWidth: 640 }}>
        ClauseRadar converts contracts into structured, evidence-backed operational obligations —
        with human verification, deterministic deadlines, explainable risk, and a tamper-resistant
        audit trail. Deterministic business logic works even when AI is unavailable.
      </p>
      <div className="cta-row">
        <Link className="btn" to="/workspace">Explore ClauseRadar</Link>
        <Link className="btn secondary" to="/register">Create Workspace</Link>
      </div>
      <div className="grid" style={{ marginTop: 28 }}>
        <div className="card"><h3>Evidence first</h3><p className="muted">Every obligation links to its source document, page, and clause text.</p></div>
        <div className="card"><h3>Human verification</h3><p className="muted">Nothing becomes operational until a reviewer confirms the source.</p></div>
        <div className="card"><h3>Deterministic deadlines</h3><p className="muted">Temporal rules are computed, tested, and timezone-aware — never guessed by AI.</p></div>
      </div>
      <p className="muted" style={{ marginTop: 20 }}>
        No signup required for evaluation. <Link to="/login">Log in</Link> if you already have a workspace.
      </p>
    </div>
  );
}
