import { useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, getErrorMessage } from '../api';
import type { Document } from '../api';
import { EmptyState, ErrorState, Loading } from '../components';

function unwrapPages(data: { results?: { page_number: number; text: string }[] } | { page_number: number; text: string }[]) {
  return Array.isArray(data) ? data : (data.results ?? []);
}

function DocStatus({ status }: { status: Document['status'] }) {
  const tone = status === 'READY' ? 'badge-ok' : status === 'FAILED' ? 'badge-bad' : 'badge-warn';
  return <span className={`badge ${tone}`}>{status}</span>;
}

export default function DocumentsSection({ contractId }: { contractId: string }) {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);
  const [openPages, setOpenPages] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const docs = useQuery({
    queryKey: ['documents', contractId],
    queryFn: () => api.documents(`?contract=${contractId}&page_size=50`),
  });

  const pages = useQuery({
    queryKey: ['documents', 'pages', openPages],
    queryFn: () => api.documentPages(openPages as string),
    enabled: Boolean(openPages),
  });

  async function handleUpload(file: File | undefined) {
    if (!file) return;
    if (!/\.(pdf|docx)$/i.test(file.name)) {
      setMessage({ kind: 'err', text: 'Only PDF or DOCX files are accepted.' });
      return;
    }
    setUploading(true);
    setMessage(null);
    try {
      const doc = await api.uploadDocument(contractId, file);
      setMessage({
        kind: doc.status === 'FAILED' ? 'err' : 'ok',
        text: doc.status === 'FAILED' ? `Processing failed: ${doc.error_message}` : `Uploaded ${doc.original_filename} — ${doc.page_count} page(s) ready.`,
      });
      await queryClient.invalidateQueries({ queryKey: ['documents'] });
      await queryClient.invalidateQueries({ queryKey: ['audit'] });
    } catch (err) {
      const existing = (err as { existing_id?: string }).existing_id;
      setMessage({
        kind: 'err',
        text: existing ? `${getErrorMessage(err)} (see existing document below)` : getErrorMessage(err, 'Upload failed.'),
      });
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  async function handleReprocess(id: string) {
    setBusyId(id);
    try {
      await api.reprocessDocument(id);
      await queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch (err) {
      setMessage({ kind: 'err', text: getErrorMessage(err, 'Reprocess failed.') });
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!window.confirm(`Delete ${name}? This removes the file and its extracted pages.`)) return;
    setBusyId(id);
    try {
      await api.deleteDocument(id);
      await queryClient.invalidateQueries({ queryKey: ['documents'] });
      await queryClient.invalidateQueries({ queryKey: ['audit'] });
    } catch (err) {
      setMessage({ kind: 'err', text: getErrorMessage(err, 'Delete failed.') });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section aria-label="Documents">
      <h2>Documents</h2>
      <div className="card">
        <label className="field">
          <span>Upload PDF or DOCX (max 25 MB)</span>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            disabled={uploading}
            onChange={(e) => handleUpload(e.target.files?.[0])}
          />
        </label>
        {uploading && <p className="muted" role="status">Uploading and processing…</p>}
        {message && (
          <p role={message.kind === 'err' ? 'alert' : 'status'} className={message.kind === 'err' ? 'form-error' : 'muted'}>
            {message.text}
          </p>
        )}
      </div>

      {docs.isPending && <Loading label="Loading documents…" />}
      {docs.isError && <ErrorState error={docs.error} onRetry={() => docs.refetch()} />}
      {docs.data && docs.data.results.length === 0 && (
        <EmptyState title="No documents yet" hint="Upload the signed PDF or DOCX to start extraction." />
      )}
      {docs.data && docs.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th scope="col">File</th><th scope="col">Status</th><th scope="col">Pages</th><th scope="col">Actions</th></tr>
            </thead>
            <tbody>
              {docs.data.results.map((d) => (
                <tr key={d.id}>
                  <td>
                    <div><strong>{d.original_filename}</strong></div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {(d.size_bytes / 1024).toFixed(1)} KB · {d.mime.split('/')[1]} {d.ocr_used ? '· OCR' : ''}
                    </div>
                    {d.status === 'FAILED' && d.error_message && (
                      <div className="form-error" style={{ fontSize: 13 }}>{d.error_message}</div>
                    )}
                  </td>
                  <td><DocStatus status={d.status} /></td>
                  <td>{d.status === 'READY' ? d.page_count : '—'}</td>
                  <td>
                    <div className="row-actions">
                      {d.status === 'READY' && (
                        <button className="btn secondary btn-sm" type="button" onClick={() => setOpenPages(openPages === d.id ? null : d.id)}>
                          {openPages === d.id ? 'Hide text' : 'View text'}
                        </button>
                      )}
                      <button className="btn secondary btn-sm" type="button" disabled={busyId === d.id} onClick={() => api.downloadDocument(d.id, d.original_filename)}>
                        Download
                      </button>
                      {d.status === 'FAILED' && (
                        <button className="btn secondary btn-sm" type="button" disabled={busyId === d.id} onClick={() => handleReprocess(d.id)}>
                          {busyId === d.id ? 'Retrying…' : 'Retry'}
                        </button>
                      )}
                      <button className="btn secondary btn-sm" type="button" disabled={busyId === d.id} onClick={() => handleDelete(d.id, d.original_filename)}>
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {openPages && (
        <div className="card">
          <h3>Extracted text — <Link to="#" onClick={(e) => { e.preventDefault(); setOpenPages(null); }}>close</Link></h3>
          {pages.isPending && <p className="muted">Loading pages…</p>}
          {pages.isError && <p className="form-error">{getErrorMessage(pages.error)}</p>}
          {pages.data && unwrapPages(pages.data as never).map((p) => (
            <article key={p.page_number} className="page-text">
              <h4>Page {p.page_number}</h4>
              <pre>{p.text || '(no text on this page)'}</pre>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
