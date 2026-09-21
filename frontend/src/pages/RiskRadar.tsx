import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, buildQuery, getErrorMessage } from '../api';
import { useAuth } from '../auth';
import { EmptyState, ErrorState, Loading, PageHeader } from '../components';

function ScoreBadge({ score, level }: { score: number; level: string }) {
  const tone = level === 'CRITICAL' ? 'badge-bad' : level === 'HIGH' ? 'badge-bad' : level === 'MEDIUM' ? 'badge-warn' : 'badge-ok';
  return <span className={`badge ${tone}`}>{score} · {level}</span>;
}

export default function RiskRadar() {
  const { user, activeWorkspace } = useAuth();
  const queryClient = useQueryClient();
  const [contractId, setContractId] = useState('');
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const contracts = useQuery({
    queryKey: ['contracts', 'risk', activeWorkspace?.id],
    queryFn: () => api.contracts(buildQuery({ workspace: activeWorkspace?.id, page_size: 100 })),
    enabled: Boolean(user && activeWorkspace),
  });
  const findings = useQuery({
    queryKey: ['risks', activeWorkspace?.id],
    queryFn: () => api.risks(buildQuery({ workspace: activeWorkspace?.id, page_size: 100 })),
    enabled: Boolean(user && activeWorkspace),
  });
  const summary = useQuery({
    queryKey: ['risks', 'summary', contractId],
    queryFn: () => api.riskSummary(contractId),
    enabled: Boolean(user && contractId),
  });

  async function onAssess() {
    if (!contractId) return;
    setBusy(true);
    setNote(null);
    try {
      await api.assessRisks(contractId);
      setNote('Risk assessment refreshed.');
      await queryClient.invalidateQueries({ queryKey: ['risks'] });
    } catch (err) {
      setNote(getErrorMessage(err, 'Assessment failed.'));
    } finally {
      setBusy(false);
    }
  }

  if (!user) return (<div><PageHeader title="Risk Radar" /><EmptyState title="Not logged in" action={<Link className="btn" to="/login">Log in</Link>} /></div>);
  if (!activeWorkspace) return (<div><PageHeader title="Risk Radar" /><EmptyState title="No workspace selected" /></div>);

  return (
    <div>
      <PageHeader
        title="Risk Radar"
        subtitle="Deterministic, explainable scores — every point cites its rule, source, and affected obligation. No black boxes."
      />
      {note && <p className="muted" role="status">{note}</p>}
      <div className="toolbar">
        <select aria-label="Select contract" value={contractId} onChange={(e) => setContractId(e.target.value)}>
          <option value="">Select a contract…</option>
          {contracts.data?.results.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
        <button className="btn" type="button" disabled={busy || !contractId} onClick={onAssess}>
          {busy ? 'Assessing…' : 'Run assessment'}
        </button>
      </div>

      {contractId && summary.isPending && <Loading label="Loading risk summary…" />}
      {contractId && summary.isError && <ErrorState error={summary.error} onRetry={() => summary.refetch()} />}
      {contractId && summary.data && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Risk score <ScoreBadge score={summary.data.score} level={summary.data.level} /></h3>
          {summary.data.findings.length === 0 && <p className="muted">No risk factors — clean contract.</p>}
          {summary.data.findings.map((f) => (
            <article key={f.id} className="finding">
              <div className="row-actions" style={{ justifyContent: 'space-between' }}>
                <strong>+{f.points} · {f.title}</strong>
                <span className="badge badge-neutral">{f.rule}</span>
              </div>
              <p className="muted" style={{ fontSize: 13 }}>{f.explanation}</p>
              {f.obligation && <p style={{ fontSize: 13 }}>Affected obligation: <Link to={`/contracts/${f.contract}`}>{f.obligation_title ?? f.obligation}</Link></p>}
            </article>
          ))}
        </div>
      )}

      <h2>All findings in workspace</h2>
      {findings.isPending && <Loading label="Loading findings…" />}
      {findings.isError && <ErrorState error={findings.error} onRetry={() => findings.refetch()} />}
      {findings.data && findings.data.results.length === 0 && (
        <EmptyState title="No risk findings" hint="Run an assessment on a contract to generate explainable findings." />
      )}
      {findings.data && findings.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th scope="col">Finding</th><th scope="col">Points</th><th scope="col">Severity</th><th scope="col">Contract</th></tr></thead>
            <tbody>
              {findings.data.results.map((f) => (
                <tr key={f.id}>
                  <td><code>{f.rule}</code> — {f.title}</td>
                  <td>+{f.points}</td>
                  <td>{f.severity}</td>
                  <td><Link to={`/contracts/${f.contract}`}>{f.contract_title}</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
