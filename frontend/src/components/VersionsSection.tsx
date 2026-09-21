import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, getErrorMessage } from '../api';
import { EmptyState, ErrorState, Loading } from '../components';

export default function VersionsSection({ contractId }: { contractId: string }) {
  const [fromV, setFromV] = useState('');
  const [toV, setToV] = useState('');
  const [runKey, setRunKey] = useState(0);

  const versions = useQuery({
    queryKey: ['versions', contractId],
    queryFn: () => api.contractVersions(contractId),
  });
  const canCompare = fromV && toV && fromV !== toV;
  const diff = useQuery({
    queryKey: ['versions', 'diff', contractId, runKey],
    queryFn: () => api.compareVersions(contractId, Number(fromV), Number(toV)),
    enabled: runKey > 0,
  });

  return (
    <section aria-label="Versions">
      <h2>Versions</h2>
      {versions.isPending && <Loading label="Loading versions…" />}
      {versions.isError && <ErrorState error={versions.error} onRetry={() => versions.refetch()} />}
      {versions.data && versions.data.length <= 1 && (
        <EmptyState title={versions.data.length === 0 ? 'No versions yet' : 'Single version'}
          hint="Upload a new document to this contract to create version 2, then compare." />
      )}
      {versions.data && versions.data.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th scope="col">Version</th><th scope="col">Document</th><th scope="col">Created</th></tr></thead>
            <tbody>
              {versions.data.map((v) => (
                <tr key={v.id}><td>v{v.version_number}</td><td>{v.document_name ?? '—'}</td><td>{new Date(v.created_at).toLocaleString()}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {versions.data && versions.data.length > 1 && (
        <form className="toolbar" onSubmit={(e) => { e.preventDefault(); if (canCompare) setRunKey((k) => k + 1); }}>
          <select aria-label="Compare from version" value={fromV} onChange={(e) => setFromV(e.target.value)}>
            <option value="">From…</option>
            {versions.data.map((v) => <option key={v.id} value={v.version_number}>v{v.version_number}</option>)}
          </select>
          <select aria-label="Compare to version" value={toV} onChange={(e) => setToV(e.target.value)}>
            <option value="">To…</option>
            {versions.data.map((v) => <option key={v.id} value={v.version_number}>v{v.version_number}</option>)}
          </select>
          <button className="btn" type="submit" disabled={!canCompare}>Compare</button>
        </form>
      )}
      {diff.isPending && <Loading label="Comparing versions…" />}
      {diff.isError && <p className="form-error">{getErrorMessage(diff.error)}</p>}
      {diff.data && (
        <div>
          <p className="muted" role="status">
            v{diff.data.from_version} → v{diff.data.to_version}: {diff.data.counts.added} added ·{' '}
            {diff.data.counts.removed} removed · {diff.data.counts.modified} modified · {diff.data.counts.unchanged} unchanged
          </p>
          {diff.data.modified.map((m, i) => (
            <article key={i} className="card">
              <span className="badge badge-warn">MODIFIED</span>
              <div className="diff-cols">
                <div><h5>Before (p{m.old.page_number})</h5><p className="diff-old">{m.old.text}</p></div>
                <div><h5>After (p{m.new.page_number})</h5><p className="diff-new">{m.new.text}</p></div>
              </div>
              <p className="muted" style={{ fontSize: 13 }}><strong>Potential impact:</strong> {m.impact}</p>
              {m.affected_obligations.length > 0 && (
                <p style={{ fontSize: 13 }}><strong>Affected obligations:</strong> {m.affected_obligations.map((o) => `${o.title} [${o.status}]`).join('; ')}</p>
              )}
            </article>
          ))}
          {diff.data.added.map((a) => (
            <article key={a.id} className="card"><span className="badge badge-ok">ADDED</span><p>{a.text}</p></article>
          ))}
          {diff.data.removed.map((r, i) => (
            <article key={i} className="card"><span className="badge badge-bad">REMOVED</span><p className="diff-old">{r.old.text}</p>
              <p className="muted" style={{ fontSize: 13 }}><strong>Potential impact:</strong> {r.impact}</p></article>
          ))}
        </div>
      )}
    </section>
  );
}
