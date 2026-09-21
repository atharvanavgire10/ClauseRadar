import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, buildQuery } from '../api';
import { EmptyState, ErrorState, Loading } from '../components';

const TYPES = ['DEFINITIONS','PAYMENT','RENEWAL','TERMINATION','INSURANCE','CONFIDENTIALITY','SECURITY','COMPLIANCE','SLA','REPORTING','AUDIT','LIABILITY','INDEMNIFICATION','NOTICE','DELIVERY','GENERAL'];

export default function ClausesSection({ contractId, onViewSource }: { contractId: string; onViewSource: (documentId: string) => void }) {
  const [typeFilter, setTypeFilter] = useState('');
  const query = buildQuery({ contract: contractId, clause_type: typeFilter || undefined, page_size: 100 });
  const list = useQuery({
    queryKey: ['clauses', contractId, typeFilter],
    queryFn: () => api.clauses(query),
  });
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <section aria-label="Clauses">
      <h2>Clauses</h2>
      <div className="toolbar">
        <select aria-label="Filter by clause type" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          <option value="">All types</option>
          {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      {list.isPending && <Loading label="Loading clauses…" />}
      {list.isError && <ErrorState error={list.error} onRetry={() => list.refetch()} />}
      {list.data && list.data.results.length === 0 && (
        <EmptyState title="No clauses found" hint="Upload a document to extract clauses, or clear the type filter." />
      )}
      {list.data && list.data.results.length > 0 && (
        <div>
          <p className="muted" role="status">{list.data.count} clause(s) detected by deterministic rules.</p>
          {list.data.results.map((c) => (
            <article key={c.id} className="card">
              <div className="row-actions" style={{ justifyContent: 'space-between' }}>
                <span className="badge badge-neutral">{c.clause_type}</span>
                <span className="muted" style={{ fontSize: 12 }}>
                  {c.document_name} · p{c.page_number} · {Math.round(c.confidence * 100)}% · {c.extraction_method}
                </span>
              </div>
              {c.heading && <h4 style={{ marginBottom: 4 }}>{c.heading}</h4>}
              <p style={{ marginTop: 4 }}>{openId === c.id ? c.text : `${c.text.slice(0, 280)}${c.text.length > 280 ? '…' : ''}`}</p>
              <div className="row-actions">
                {c.text.length > 280 && (
                  <button className="btn secondary btn-sm" type="button" onClick={() => setOpenId(openId === c.id ? null : c.id)}>
                    {openId === c.id ? 'Collapse' : 'Expand'}
                  </button>
                )}
                <button className="btn secondary btn-sm" type="button" onClick={() => onViewSource(c.document)}>
                  View source
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
