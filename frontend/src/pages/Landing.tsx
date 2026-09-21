import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api, getErrorMessage } from '../api';
import { useAuth } from '../auth';

export default function Landing() {
  const { explore } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const evalInfo = useQuery({ queryKey: ['eval-info'], queryFn: api.evalInfo, staleTime: 60_000, retry: 1 });

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
      <div className="card" style={{ maxWidth: 640 }}>
        <h3 style={{ marginTop: 0 }}>Try it now — no account, no API key</h3>
        {evalInfo.isPending && <p className="muted">Checking evaluation workspace…</p>}
        {evalInfo.isError && <p className="muted">Evaluation workspace status unavailable (is the API running?).</p>}
        {evalInfo.data && evalInfo.data.seeded && (
          <p className="muted">
            Live demo data: {evalInfo.data.contracts} contracts · {evalInfo.data.clauses} clauses ·{' '}
            {evalInfo.data.obligations} obligations with evidence, deadlines, risk scores, and audit history.
          </p>
        )}
        <div className="cta-row">
          <button className="btn" type="button" onClick={onExplore} disabled={busy}>
            {busy ? 'Opening…' : 'Explore ClauseRadar'}
          </button>
          <Link className="btn secondary" to="/register">Create Workspace</Link>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <p className="muted" style={{ fontSize: 13 }}>No signup needed — Explore opens a real, seeded evaluation workspace backed by the same API.</p>
      </div>
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
