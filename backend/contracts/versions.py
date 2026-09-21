"""Version bookkeeping + comparison service."""
from __future__ import annotations

from django.db import transaction

from audit.services import log_event
from .diff import compare_clause_lists
from .models import ContractVersion


def ensure_version_for_document(document_id) -> ContractVersion | None:
    """Create the next ContractVersion for a document (idempotent)."""
    from documents.models import Document

    with transaction.atomic():
        doc = Document.objects.select_for_update().get(pk=document_id)
        existing = ContractVersion.objects.filter(document=doc).first()
        if existing:
            return existing
        last = ContractVersion.objects.filter(contract=doc.contract).order_by("-version_number").first()
        number = (last.version_number + 1) if last else 1
        version = ContractVersion.objects.create(
            contract=doc.contract, version_number=number, document=doc, created_by=doc.created_by,
            notes=f"Uploaded {doc.original_filename}",
        )
        log_event(actor=doc.created_by, organization=doc.workspace.organization, workspace=doc.workspace,
                  entity_type="contract", entity_id=doc.contract_id, action="contract.version_created",
                  metadata={"version": number, "document": str(doc.id)})
        return version


def ensure_versions_for_contract(contract_id) -> int:
    """Backfill versions for documents predating versioning. Returns created count."""
    from documents.models import Document

    made = 0
    for doc in Document.objects.filter(contract_id=contract_id).order_by("created_at"):
        before = ContractVersion.objects.filter(contract_id=contract_id).count()
        ensure_version_for_document(doc.id)
        if ContractVersion.objects.filter(contract_id=contract_id).count() > before:
            made += 1
    return made


def compare_versions(contract_id, from_number: int, to_number: int) -> dict:
    """Compare two versions; attaches affected obligations to modified/removed."""
    from clauses.models import Clause
    from contracts.models import Contract
    from obligations.models import Obligation

    contract = Contract.objects.get(pk=contract_id)
    ensure_versions_for_contract(contract_id)
    v1 = ContractVersion.objects.filter(contract=contract, version_number=from_number).select_related("document").first()
    v2 = ContractVersion.objects.filter(contract=contract, version_number=to_number).select_related("document").first()
    if v1 is None or v2 is None:
        raise ValueError(f"Versions {from_number} → {to_number} not found for this contract.")

    def as_dicts(version):
        if version.document_id is None:
            return []
        return [{"id": str(c.id), "clause_type": c.clause_type, "heading": c.heading,
                 "text": c.text, "page_number": c.page_number}
                for c in Clause.objects.filter(document_id=version.document_id)
                .order_by("page_number", "start_offset")]

    result = compare_clause_lists(as_dicts(v1), as_dicts(v2))

    def attach_affected(entries, key):
        from uuid import UUID

        def base_id(raw: str) -> str | None:
            raw = raw.split(":s")[0]
            try:
                UUID(raw)
            except (ValueError, AttributeError):
                return None
            return raw

        for entry in entries:
            old_clause_id = base_id(entry[key]["id"])
            affected = list(Obligation.objects.filter(clause_id=old_clause_id)
                            .values("id", "title", "status", "obligation_type")) if old_clause_id else []
            entry["affected_obligations"] = [
                {"id": str(a["id"]), "title": a["title"], "status": a["status"], "type": a["obligation_type"]}
                for a in affected
            ]
            entry["impact"] = entry.get("impact") or "Clause removed — linked obligations may no longer have evidence."
        return entries

    result["modified"] = attach_affected(result["modified"], "old")
    removed = [{"old": r, "affected_obligations": [], "impact": "Clause removed — linked obligations may no longer have evidence."} for r in result["removed"]]
    for entry in removed:
        affected = list(Obligation.objects.filter(clause_id=entry["old"]["id"])
                        .values("id", "title", "status", "obligation_type"))
        entry["affected_obligations"] = [
            {"id": str(a["id"]), "title": a["title"], "status": a["status"], "type": a["obligation_type"]}
            for a in affected
        ]
    result["removed"] = removed
    result["from_version"] = from_number
    result["to_version"] = to_number
    result["contract"] = str(contract.id)
    return result
