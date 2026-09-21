from celery import shared_task

from .services import process_document


@shared_task(bind=True, max_retries=2, name="documents.process_document")
def process_document_task(self, document_id: str, force: bool = False) -> str:
    """Background processing with idempotency guard in process_document()."""
    try:
        doc = process_document(document_id, force=force)
        return str(doc.status)
    except Exception as exc:  # pragma: no cover - task-level safety net
        try:
            self.retry(exc=exc, countdown=10)
        except self.MaxRetriesExceededError:
            pass
        raise
