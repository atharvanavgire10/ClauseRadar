import { EmptyState, PageHeader } from '../components';

const COPY: Record<string, { hint: string }> = {
  Obligations: { hint: 'Structured obligations with human verification land in Phases 05–06. Data shown here will come from the live API — no fixture numbers.' },
  Deadlines: { hint: 'The deterministic deadline engine lands in Phase 07 with timezone-aware calculations and extensive unit tests.' },
  'Risk Radar': { hint: 'Explainable, rule-based risk scoring lands in Phase 09. Every finding will cite its rule, score contribution, and source.' },
};

export default function FuturePlaceholder({ title }: { title: string }) {
  return (
    <div>
      <PageHeader title={title} subtitle="This module is scaffolded and ships in its dedicated phase." />
      <EmptyState title={`No ${title.toLowerCase()} yet`} hint={COPY[title]?.hint ?? 'Coming in its dedicated phase.'} />
    </div>
  );
}
