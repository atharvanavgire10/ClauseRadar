import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, buildQuery } from '../api';
import { useAuth } from '../auth';
import { ObligationCard } from '../components/ObligationsSection';
import { EmptyState, ErrorState, Loading, PageHeader } from '../components';

const STATUSES = ['NEEDS_REVIEW','CONFIRMED','REJECTED','ACTIVE','IN_PROGRESS','COMPLETED','WAIVED'];
const TYPES = ['INSURANCE','PAYMENT','REPORTING','RENEWAL_NOTICE','TERMINATION_NOTICE','COMPLIANCE','SLA','CONFIDENTIALITY','SECURITY','AUDIT','DELIVERY','GENERAL'];

export default function Obligations() {
  const { user, activeWorkspace } = useAuth();
  const [statusFilter, setStatusFilter] = useState('NEEDS_REVIEW');
  const [typeFilter, setTypeFilter] = useState('');
  const query = buildQuery({ workspace: activeWorkspace?.id, status: statusFilter || undefined, obligation_type: typeFilter || undefined, page_size: 50 });
  const list = useQuery({
    queryKey: ['obligations', 'workspace', activeWorkspace?.id, statusFilter, typeFilter],
    queryFn: () => api.obligations(query),
    enabled: Boolean(user && activeWorkspace),
  });

  if (!user) return (<div><PageHeader title="Obligations" /><EmptyState title="Not logged in" action={<Link className="btn" to="/login">Log in</Link>} /></div>);
  if (!activeWorkspace) return (<div><PageHeader title="Obligations" /><EmptyState title="No workspace selected" /></div>);

  const needsReview = list.data?.results.filter((o) => o.status === 'NEEDS_REVIEW').length ?? 0;

  return (
    <div>
      <PageHeader
        title="Obligations"
        subtitle={`${needsReview} awaiting review in ${activeWorkspace.organization_slug}/${activeWorkspace.slug}. Every item links to its source evidence.`}
      />
      <div className="toolbar" role="search">
        <select aria-label="Filter by status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select aria-label="Filter by type" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          <option value="">All types</option>
          {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      {list.isPending && <Loading label="Loading obligations…" />}
      {list.isError && <ErrorState error={list.error} onRetry={() => list.refetch()} />}
      {list.data && list.data.results.length === 0 && (
        <EmptyState title="No obligations in this state" hint="Upload contract documents — extracted obligations arrive as NEEDS_REVIEW." />
      )}
      {list.data?.results.map((ob) => <ObligationCard key={ob.id} ob={ob} onChanged={() => list.refetch()} />)}
    </div>
  );
}
