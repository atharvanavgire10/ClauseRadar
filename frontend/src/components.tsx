import type { ReactNode } from 'react';
import { getErrorMessage } from './api';

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="card" role="status" aria-live="polite">
      <p className="muted">{label}</p>
    </div>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="card" role="status">
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      {hint && <p className="muted">{hint}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div className="card" role="alert">
      <h3 style={{ marginTop: 0 }}>Something went wrong</h3>
      <p className="muted">{getErrorMessage(error)}</p>
      {onRetry && (
        <button className="btn secondary" type="button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="page-header">
      <div>
        <h1 style={{ marginBottom: 4 }}>{title}</h1>
        {subtitle && <p className="muted" style={{ marginTop: 0 }}>{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

export function StatusBadge({ value }: { value: string }) {
  const tone =
    value === 'ACTIVE' ? 'ok' : value === 'OVERDUE' ? 'bad' : value === 'DRAFT' ? 'neutral' : value === 'ARCHIVED' ? 'neutral' : 'warn';
  return <span className={`badge badge-${tone}`}>{value}</span>;
}
