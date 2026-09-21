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
                used_method = method
                if method in ("RULE", "HYBRID"):
                    try:
                        from ai.service import classify_clause_ai, get_provider

                        if get_provider() is not None:
                            ai_result = classify_clause_ai(f"{heading}\n{text}" if heading else text)
                            if ai_result is not None:
                                used_method = "HYBRID" if ai_result["clause_type"] == clause_type else "LLM"
                                clause_type, confidence = ai_result["clause_type"], ai_result["confidence"]
                    except Exception:  # pragma: no cover - AI must never break extraction
                        pass
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
                        extraction_method=used_method if used_method in ("RULE", "LLM", "HYBRID") else "RULE",
                    )
                )
        Clause.objects.bulk_create(clauses)
        log_event(
            actor=doc.created_by, organization=doc.workspace.organization, workspace=doc.workspace,
            entity_type="document", entity_id=doc.id, action="document.clauses_extracted",
            metadata={"clauses": len(clauses), "method": method, "contract": str(doc.contract_id)},
        )
        count = len(clauses)
    # Obligation extraction follows clause extraction (best-effort, never fatal).
    try:
        from obligations.services import extract_obligations_for_document

        extract_obligations_for_document(document_id, method=method)
    except Exception:  # pragma: no cover
        pass
    return count
