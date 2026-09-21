# Document pipeline (Phase 03)

## Upload
`POST /api/v1/documents/` (multipart: `contract=<uuid>`, `file=<pdf|docx>`).
Writer role on the contract's workspace required.

Validation (never trust the client):
- extension must be `.pdf`/`.docx` **and** magic bytes must agree
  (`%PDF` / ZIP `PK\x03\x04`) — renamed executables rejected (400 `unsupported_type`)
- size cap from `MAX_UPLOAD_MB` (default 25 MB) → 400 `file_too_large`
- SHA-256 duplicate detection per workspace → 409 `duplicate` + `existing_id`
- filename sanitized (basename, safe chars, ≤200 chars)

## States
`UPLOADED → PROCESSING → READY | FAILED`. Processing runs inline when
`CELERY_TASK_ALWAYS_EAGER=True` (local dev) or via `documents.process_document`
Celery task with a worker. `READY` documents are skipped on re-dispatch unless
`force=True` (`POST /api/v1/documents/{id}/reprocess/`), so retries never
duplicate pages (pages deleted + bulk-created inside one transaction).

## Extraction
- PDF: PyMuPDF per-page text. Text-empty pages try OCR (`pytesseract`, if the
  binary is installed); otherwise the page stays empty and `ocr_used` records
  whether OCR contributed.
- DOCX: python-docx paragraphs + tables, chunked into ~4000-char pseudo-pages
  (DOCX has no native pages).
- Zero readable text anywhere → `FAILED` with a human message explaining the
  likely scanned-image cause instead of pretending success.

## Reading
- `GET /api/v1/documents/?contract=&workspace=&status=` (membership-scoped)
- `GET /api/v1/documents/{id}/pages/` — ordered extracted text
- `GET /api/v1/documents/{id}/download/` — authenticated file response
- `DELETE /api/v1/documents/{id}/` — removes DB rows + stored file (audited)

Every transition writes audit events: `document.uploaded`,
`document.processing_started`, `document.processed`, `document.processing_failed`,
`contract.document_processed`, `document.deleted`.
