"""Clause extraction service — idempotent per document."""
from __future__ import annotations

from django.db import transaction

from audit.services import log_event
from .detector import classify, segment_page
from .models import Clause


def extract_clauses_for_document(document_id, *, method: str = "RULE") -> int:
    """(Re)build clauses for a READY document. Returns clause count."""
    from documents.models import Document

    with transaction.atomic():
        doc = Document.objects.select_for_update().get(pk=document_id)
        Clause.objects.filter(document=doc).delete()
        if doc.status != "READY":
            return 0
        pages = list(doc.pages.order_by("page_number").all())
        clauses: list[Clause] = []
        for page in pages:
            for heading, text, start, end in segment_page(page.text or ""):
                clause_type, confidence = classify(f"{heading}\n{text}" if heading else text)
                clauses.append(
                    Clause(
                        workspace=doc.workspace,
                        contract=doc.contract,
                        document=doc,
                        page=page,
                        page_number=page.page_number,
                        heading=heading[:300],
                        text=text,
                        clause_type=clause_type,
                        start_offset=start,
                        end_offset=end,
                        confidence=confidence,
                        extraction_method=method,
                    )
                )
        Clause.objects.bulk_create(clauses)
        log_event(
            actor=doc.created_by, organization=doc.workspace.organization, workspace=doc.workspace,
            entity_type="document", entity_id=doc.id, action="document.clauses_extracted",
            metadata={"clauses": len(clauses), "method": method, "contract": str(doc.contract_id)},
        )
        return len(clauses)
