"""Document processing pipeline — synchronous service + Celery task wrapper.

Runs eagerly when Redis is unavailable (CELERY_TASK_ALWAYS_EAGER), so uploads
work in local dev without a worker. Idempotent: READY documents are skipped
unless force=True; concurrent retries never duplicate pages.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from audit.services import log_event
from .extraction import extract_docx_pages, extract_pdf_pages
from .models import Document, DocumentPage


def process_document(document_id, *, force: bool = False) -> Document:
    from django.core.files.storage import default_storage

    with transaction.atomic():
        doc = Document.objects.select_for_update().get(pk=document_id)
        if doc.status == Document.Status.READY and not force:
            return doc
        if doc.status == Document.Status.PROCESSING and not force:
            return doc
        doc.status = Document.Status.PROCESSING
        doc.error_message = ""
        doc.save(update_fields=["status", "error_message", "updated_at"])
        log_event(
            actor=doc.created_by, organization=doc.workspace.organization, workspace=doc.workspace,
            entity_type="document", entity_id=doc.id, action="document.processing_started",
            metadata={"filename": doc.original_filename},
        )

    try:
        if not doc.file or not default_storage.exists(doc.file.name):
            raise RuntimeError("Stored file is missing.")
        file_path = default_storage.path(doc.file.name)
        if doc.mime == "application/pdf":
            page_texts, ocr_used = extract_pdf_pages(file_path)
        elif doc.mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            page_texts, ocr_used = extract_docx_pages(file_path)
        else:
            raise RuntimeError(f"Unsupported document type: {doc.mime}")
        if not any(t.strip() for t in page_texts):
            raise RuntimeError(
                "No readable text found. The file may be a scanned image — "
                "OCR is unavailable in this environment."
            )
    except Exception as exc:
        with transaction.atomic():
            doc = Document.objects.select_for_update().get(pk=document_id)
            doc.status = Document.Status.FAILED
            doc.error_message = str(exc)[:2000]
            doc.processed_at = timezone.now()
            doc.save(update_fields=["status", "error_message", "processed_at", "updated_at"])
            log_event(
                actor=doc.created_by, organization=doc.workspace.organization, workspace=doc.workspace,
                entity_type="document", entity_id=doc.id, action="document.processing_failed",
                metadata={"error": str(exc)[:500]},
            )
        return doc

    with transaction.atomic():
        doc = Document.objects.select_for_update().get(pk=document_id)
        DocumentPage.objects.filter(document=doc).delete()
        pages = [
            DocumentPage(document=doc, page_number=i + 1, text=text or "")
            for i, text in enumerate(page_texts)
        ]
        DocumentPage.objects.bulk_create(pages)
        doc.status = Document.Status.READY
        doc.page_count = len(pages)
        doc.ocr_used = ocr_used
        doc.error_message = ""
        doc.processed_at = timezone.now()
        doc.save(update_fields=["status", "page_count", "ocr_used", "error_message", "processed_at", "updated_at"])
        log_event(
            actor=doc.created_by, organization=doc.workspace.organization, workspace=doc.workspace,
            entity_type="document", entity_id=doc.id, action="document.processed",
            metadata={"pages": len(pages), "ocr_used": ocr_used, "contract": str(doc.contract_id)},
        )
        log_event(
            actor=doc.created_by, organization=doc.workspace.organization, workspace=doc.workspace,
            entity_type="contract", entity_id=doc.contract_id, action="contract.document_processed",
            metadata={"document": str(doc.id), "pages": len(pages)},
        )
    return doc
