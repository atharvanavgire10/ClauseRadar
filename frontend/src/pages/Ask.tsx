import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, getErrorMessage } from '../api';
import type { QAResponse } from '../api';
import { useAuth } from '../auth';
import { EmptyState, Loading, PageHeader } from '../components';

const EXAMPLES = [
  'What insurance obligations exist?',
  'What are the renewal deadlines?',
  'Which obligations are overdue?',
  'Which contracts contain termination notice periods?',
];

export default function Ask() {
  const { user, activeWorkspace } = useAuth();
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [response, setResponse] = useState<QAResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onAsk(e: FormEvent, q?: string) {
    e.preventDefault();
    const query = (q ?? question).trim();
    if (query.length < 5 || !activeWorkspace) return;
    setAsking(true);
    setError(null);
    try {
      const res = await api.askQA({ workspace: activeWorkspace.id, question: query });
      setResponse(res);
      setQuestion(query);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not answer.'));
    } finally {
      setAsking(false);
    }
  }

  if (!user) return (<div><PageHeader title="Ask ClauseRadar" /><EmptyState title="Not logged in" action={<Link className="btn" to="/login">Log in</Link>} /></div>);
  if (!activeWorkspace) return (<div><PageHeader title="Ask ClauseRadar" /><EmptyState title="No workspace selected" /></div>);

  return (
    <div>
      <PageHeader title="Ask ClauseRadar" subtitle="Evidence-grounded answers — every claim cites its source. Insufficient evidence is reported, never invented." />
      <form className="toolbar" role="search" onSubmit={onAsk}>
        <input aria-label="Ask a question" placeholder="Ask about obligations, deadlines, insurance…" value={question} onChange={(e) => setQuestion(e.target.value)} />
        <button className="btn" type="submit" disabled={asking || question.trim().length < 5}>{asking ? 'Asking…' : 'Ask'}</button>
      </form>
      <div className="row-actions" style={{ marginBottom: 12 }}>
        {EXAMPLES.map((ex) => (
          <button key={ex} className="btn secondary btn-sm" type="button" onClick={(e) => onAsk(e, ex)}>{ex}</button>
        ))}
      </div>
      {asking && <Loading label="Searching evidence…" />}
      {error && <p className="form-error" role="alert">{error}</p>}
      {response && (
        <div className="card">
          <p style={{ whiteSpace: 'pre-wrap' }}>{response.answer}</p>
          <h4>Cited sources ({response.citations.length})</h4>
          {response.citations.length === 0 && <p className="muted">No sources — the answer states insufficient evidence.</p>}
          {response.citations.map((c, i) => (
            <blockquote key={i} className="evidence">
              <div className="muted" style={{ fontSize: 12 }}>
                [{i + 1}] {c.document_name ?? 'workspace record'}
                {c.page_number ? ` · p${c.page_number}` : ''}
                {c.contract_id ? <> · <Link to={`/contracts/${c.contract_id}`}>open source</Link></> : null}
              </div>
              {c.source_text}
            </blockquote>
          ))}
        </div>
      )}
    </div>
  );
}
