import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, buildQuery } from '../api';
import { useAuth } from '../auth';
import { EmptyState, ErrorState, Loading, PageHeader, StatusBadge } from '../components';

export default function SearchPage() {
  const { user, activeWorkspace } = useAuth();
  const [term, setTerm] = useState('insurance');
  const [submitted, setSubmitted] = useState('');
  const results = useQuery({
    queryKey: ['contracts', 'search', activeWorkspace?.id, submitted],
    queryFn: () => api.contracts(buildQuery({ workspace: activeWorkspace?.id, search: submitted })),
    enabled: Boolean(user && activeWorkspace && submitted),
  });

  if (!user) return (<div><PageHeader title="Search" /><EmptyState title="Not logged in" action={<Link className="btn" to="/login">Log in</Link>} /></div>);

  return (
    <div>
      <PageHeader title="Search" subtitle="Live full API search over contracts. Clause, obligation, and evidence search land with Phase 12." />
      <form className="toolbar" role="search" onSubmit={(e) => { e.preventDefault(); setSubmitted(term.trim()); }}>
        <input aria-label="Search contracts" placeholder="Try: insurance, renewal, vendor…" value={term} onChange={(e) => setTerm(e.target.value)} />
        <button className="btn" type="submit">Search</button>
      </form>
      {!submitted && <EmptyState title="Search your contracts" hint="Enter a term above — queries hit the live backend API." />}
      {results.isPending && submitted && <Loading label={`Searching for “${submitted}”…`} />}
      {results.isError && <ErrorState error={results.error} onRetry={() => results.refetch()} />}
      {results.data && (
        <p className="muted" role="status">{results.data.count} result(s) for “{submitted}”.</p>
      )}
      {results.data && results.data.results.length > 0 && (
        <div className="table-wrap"><table>
          <thead><tr><th scope="col">Title</th><th scope="col">Counterparty</th><th scope="col">Status</th></tr></thead>
          <tbody>{results.data.results.map((c) => (
            <tr key={c.id}><td><Link to={`/contracts/${c.id}`}>{c.title}</Link></td><td>{c.counterparty || '—'}</td><td><StatusBadge value={c.status} /></td></tr>
          ))}</tbody>
        </table></div>
      )}
    </div>
  );
}
