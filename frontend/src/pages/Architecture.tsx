import { PageHeader } from '../components';

export default function Architecture() {
  return (
    <div>
      <PageHeader title="Architecture" subtitle="How ClauseRadar is built — deterministic core, optional AI." />
      <div className="card flow">
        <p><strong>Pipeline:</strong></p>
        <p className="muted">
          ingest → process → extract clauses → extract obligations → human verification →
          deadlines → recurrence → risk → assignment → tracking → audit → search →
          version comparison → evidence-grounded AI → notifications → public evaluation
        </p>
        <ul>
          <li><strong>Backend:</strong> Django + DRF + PostgreSQL + Celery + Redis.</li>
          <li><strong>Documents:</strong> PyMuPDF / python-docx with page segmentation and OCR fallback.</li>
          <li><strong>Deterministic engines:</strong> deadline math, recurrence, risk rules, and version diffs never depend on an LLM.</li>
          <li><strong>Evidence-first:</strong> every fact links to source document, page, clause, and text with confidence and review status.</li>
          <li><strong>Public evaluation:</strong> same APIs and business logic as authenticated workspaces, isolated and rate-limited.</li>
        </ul>
        <p className="muted">Full system docs live in <code>docs/architecture.md</code>, <code>docs/database.md</code>, and <code>docs/api.md</code>.</p>
      </div>
    </div>
  );
}
