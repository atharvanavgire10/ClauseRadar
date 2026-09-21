import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, buildQuery, getErrorMessage } from '../api';
import { useAuth } from '../auth';
import { splitHighlight } from '../highlight';
import { EmptyState, ErrorState, Loading, PageHeader } from '../components';

const TYPES = ['contract', 'document', 'clause', 'obligation', 'evidence'];

function HitLink({ hit }: { hit: { type: string; id: string; title: string; contract_id: string | null } }) {
  if (hit.type === 'contract' || (hit.contract_id && hit.type !== 'obligation')) {
    const cid = hit.type === 'contract' ? hit.id : hit.contract_id;
    return <Link to={`/contracts/${cid}`}>{hit.title}</Link>;
  }
  if (hit.type === 'obligation' && hit.contract_id) {
    return <Link to={`/contracts/${hit.contract_id}`}>{hit.title}</Link>;
  }
  return <span>{hit.title}</span>;
}

export default function SearchPage() {
  const { user, activeWorkspace } = useAuth();
  const [term, setTerm] = useState('insurance');
  const [submitted, setSubmitted] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const results = useQuery({
    queryKey: ['search', activeWorkspace?.id, submitted, typeFilter],
    queryFn: () => api.unifiedSearch(buildQuery({
      q: submitted, types: typeFilter || undefined, workspace: activeWorkspace?.id, limit: 50,
    })),
    enabled: Boolean(user && activeWorkspace && submitted),
  });

  if (!user) return (<div><PageHeader title="Search" /><EmptyState title="Not logged in" action={<Link className="btn" to="/login">Log in</Link>} /></div>);

  return (
    <div>
      <PageHeader title="Search" subtitle="Ranked full-text search across contracts, documents, clauses, obligations, and evidence." />
      <form className="toolbar" role="search" onSubmit={(e) => { e.preventDefault(); setSubmitted(term.trim()); }}>
        <input aria-label="Search everything" placeholder="Try: insurance, renewal, vendor…" value={term} onChange={(e) => setTerm(e.target.value)} />
        <select aria-label="Filter by type" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          <option value="">All types</option>
          {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <button className="btn" type="submit">Search</button>
      </form>
      {!submitted && <EmptyState title="Search everything" hint="Enter a term above — queries hit the live backend API." />}
      {results.isPending && submitted && <Loading label={`Searching for “${submitted}”…`} />}
      {results.isError && <ErrorState error={results.error} onRetry={() => results.refetch()} />}
      {results.data && (
        <p className="muted" role="status">
          {results.data.count} result(s) for “{results.data.query}”
          {Object.entries(results.data.counts).map(([t, n]) => ` · ${t}: ${n}`).join('')}
        </p>
      )}
      {results.data?.results.map((hit) => {
        const [before, mark, after] = splitHighlight(hit.snippet, submitted);
        return (
          <article key={`${hit.type}-${hit.id}`} className="card">
            <div className="row-actions" style={{ justifyContent: 'space-between' }}>
              <HitLink hit={hit} />
              <span className="badge badge-neutral">{hit.type}</span>
            </div>
            {hit.subtitle && <p className="muted" style={{ fontSize: 12, margin: '2px 0' }}>{hit.subtitle}</p>}
            <p style={{ fontSize: 13 }}>{mark ? <>{before}<mark>{mark}</mark>{after}</> : hit.snippet}</p>
          </article>
        );
      })}
      {results.data && results.data.results.length === 0 && (
        <EmptyState title="No matches" hint={`Nothing found for “${submitted}”. ${getErrorMessage(null, '')}`} />
      )}
    </div>
  );
}
