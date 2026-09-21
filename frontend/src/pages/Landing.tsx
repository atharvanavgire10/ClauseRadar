import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getErrorMessage } from '../api';
import { useAuth } from '../auth';

export default function Landing() {
  const { explore } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onExplore() {
    setBusy(true);
    setError(null);
    try {
      await explore();
      navigate('/');
    } catch (err) {
      setError(getErrorMessage(err, 'Could not open the evaluation workspace.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="landing">
      <p className="eyebrow">Contract obligation &amp; risk management</p>
      <h1>ClauseRadar</h1>
      <p className="lede">From contract clauses to actions.</p>
      <p className="muted" style={{ maxWidth: 640 }}>
        ClauseRadar converts contracts into structured, evidence-backed operational
        obligations — with human verification, deterministic deadlines, explainable
        risk, and a tamper-resistant audit trail. Deterministic business logic works
        even when AI is unavailable.
      </p>
      <div className="cta-row">
        <button className="btn" type="button" onClick={onExplore} disabled={busy}>
          {busy ? 'Opening…' : 'Explore ClauseRadar'}
        </button>
        <Link className="btn secondary" to="/register">Create Workspace</Link>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <p className="muted">No signup needed — Explore opens a real, seeded evaluation workspace backed by the same API.</p>
      <div className="grid" style={{ marginTop: 28 }}>
        <div className="card"><h3>Evidence first</h3><p className="muted">Every obligation links to its source document, page, and clause text.</p></div>
        <div className="card"><h3>Human verification</h3><p className="muted">Nothing becomes operational until a reviewer confirms the source.</p></div>
        <div className="card"><h3>Deterministic deadlines</h3><p className="muted">Temporal rules are computed, tested, and timezone-aware — never guessed by AI.</p></div>
      </div>
      <p className="muted" style={{ marginTop: 20 }}>
        Already have a workspace? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
