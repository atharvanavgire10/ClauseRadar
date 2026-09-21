from celery import shared_task

from .services import extract_clauses_for_document


@shared_task(name="clauses.extract_for_document")
def extract_clauses_task(document_id: str) -> int:
    return extract_clauses_for_document(document_id)
