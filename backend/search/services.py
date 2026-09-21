"""Unified search — PostgreSQL full-text when available, ORM fallback otherwise.

Same response shape on both backends: ranked results with snippets across
contracts, documents, clauses, obligations, and evidence.
"""
from __future__ import annotations

from django.db import connection
from django.db.models import Q

SEARCHABLE_TYPES = ("contract", "document", "clause", "obligation", "evidence")


def _is_postgres() -> bool:
    return connection.vendor == "postgresql"


def snippet(text: str, query: str, width: int = 200) -> str:
    """Center a snippet on the first query-term hit; plain text (XSS-safe)."""
    if not text:
        return ""
    terms = [t for t in query.split() if len(t) >= 2]
    lowered = text.lower()
    idx = -1
    for term in terms:
        idx = lowered.find(term.lower())
        if idx >= 0:
            break
    if idx < 0:
        return text[:width] + ("…" if len(text) > width else "")
    start = max(0, idx - width // 3)
    end = min(len(text), start + width)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end].strip() + suffix


def _pg_search(queryset, vector_fields: list[str], query: str):
    from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

    vector = SearchVector(*vector_fields)
    sq = SearchQuery(query, search_type="plain")
    return queryset.annotate(rank=SearchRank(vector, sq)).filter(rank__gt=0).order_by("-rank")


def _fallback_rank(text: str, query: str) -> float:
    terms = [t.lower() for t in query.split() if len(t) >= 2]
    if not terms:
        return 0
    lowered = text.lower()
    hits = sum(lowered.count(t) for t in terms)
    coverage = sum(1 for t in terms if t in lowered) / len(terms)
    return round(hits * coverage, 3)


def search_workspace(*, user, query: str, types: list[str] | None = None,
                     workspace_id: str | None = None, contract_id: str | None = None,
                     obligation_type: str | None = None, risk_min: int | None = None,
                     date_from=None, date_to=None, limit: int = 50) -> dict:
    """Run a workspace-scoped search. Raises ValueError on empty query."""
    query = (query or "").strip()
    if len(query) < 2:
        raise ValueError("Search query must be at least 2 characters.")
    types = [t for t in (types or list(SEARCHABLE_TYPES)) if t in SEARCHABLE_TYPES] or list(SEARCHABLE_TYPES)

    from clauses.models import Clause
    from contracts.models import Contract
    from documents.models import Document
    from obligations.models import Obligation
    from workflows.models import Evidence

    member_filter = {"workspace__memberships__user": user} if not user.is_superuser else {}
    results: list[dict] = []

    def scoped(qs, ws_field="workspace"):
        if member_filter:
            qs = qs.filter(**{f"{ws_field}__memberships__user": user}).distinct()
        if workspace_id:
            qs = qs.filter(**{ws_field + "_id": workspace_id})
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    if "contract" in types:
        qs = scoped(Contract.objects.all())
        if contract_id:
            qs = qs.filter(pk=contract_id)
        if _is_postgres():
            for row in _pg_search(qs, ["title", "counterparty", "description"], query)[:limit]:
                results.append({"type": "contract", "id": str(row.id), "title": row.title,
                                "subtitle": row.counterparty, "snippet": snippet(row.description or row.title, query),
                                "rank": float(getattr(row, "rank", 0)), "contract_id": str(row.id)})
        else:
            for row in qs.filter(Q(title__icontains=query) | Q(counterparty__icontains=query) | Q(description__icontains=query))[:limit]:
                hay = f"{row.title} {row.counterparty} {row.description}"
                results.append({"type": "contract", "id": str(row.id), "title": row.title,
                                "subtitle": row.counterparty, "snippet": snippet(hay, query),
                                "rank": _fallback_rank(hay, query), "contract_id": str(row.id)})

    if "document" in types:
        qs = scoped(Document.objects.all())
        if contract_id:
            qs = qs.filter(contract_id=contract_id)
        for row in qs.filter(original_filename__icontains=query)[:limit]:
            results.append({"type": "document", "id": str(row.id), "title": row.original_filename,
                            "subtitle": row.status, "snippet": snippet(row.original_filename, query),
                            "rank": _fallback_rank(row.original_filename, query),
                            "contract_id": str(row.contract_id)})

    if "clause" in types:
        qs = scoped(Clause.objects.all())
        if contract_id:
            qs = qs.filter(contract_id=contract_id)
        if _is_postgres():
            for row in _pg_search(qs, ["heading", "text"], query)[:limit]:
                results.append({"type": "clause", "id": str(row.id),
                                "title": row.heading or f"{row.clause_type} clause",
                                "subtitle": f"{row.clause_type} · p{row.page_number}",
                                "snippet": snippet(row.text, query), "rank": float(getattr(row, "rank", 0)),
                                "contract_id": str(row.contract_id), "document_id": str(row.document_id)})
        else:
            for row in qs.filter(Q(heading__icontains=query) | Q(text__icontains=query))[:limit]:
                hay = f"{row.heading} {row.text}"
                results.append({"type": "clause", "id": str(row.id),
                                "title": row.heading or f"{row.clause_type} clause",
                                "subtitle": f"{row.clause_type} · p{row.page_number}",
                                "snippet": snippet(row.text, query), "rank": _fallback_rank(hay, query),
                                "contract_id": str(row.contract_id), "document_id": str(row.document_id)})

    if "obligation" in types:
        qs = scoped(Obligation.objects.all())
        if contract_id:
            qs = qs.filter(contract_id=contract_id)
        if obligation_type:
            qs = qs.filter(obligation_type=obligation_type)
        if risk_min is not None:
            qs = qs.filter(risk_findings__points__gte=risk_min).distinct()
        if _is_postgres():
            for row in _pg_search(qs, ["title", "actor", "action", "source_text"], query)[:limit]:
                results.append({"type": "obligation", "id": str(row.id), "title": row.title,
                                "subtitle": f"{row.obligation_type} · {row.status}",
                                "snippet": snippet(row.source_text or row.title, query),
                                "rank": float(getattr(row, "rank", 0)), "contract_id": str(row.contract_id)})
        else:
            filt = (Q(title__icontains=query) | Q(actor__icontains=query)
                    | Q(action__icontains=query) | Q(source_text__icontains=query))
            for row in qs.filter(filt)[:limit]:
                hay = f"{row.title} {row.actor} {row.action} {row.source_text}"
                results.append({"type": "obligation", "id": str(row.id), "title": row.title,
                                "subtitle": f"{row.obligation_type} · {row.status}",
                                "snippet": snippet(row.source_text or row.title, query),
                                "rank": _fallback_rank(hay, query), "contract_id": str(row.contract_id)})

    if "evidence" in types:
        qs = scoped(Evidence.objects.all())
        for row in qs.filter(Q(original_filename__icontains=query) | Q(note__icontains=query))[:limit]:
            results.append({"type": "evidence", "id": str(row.id), "title": row.original_filename,
                            "subtitle": row.note, "snippet": snippet(f"{row.original_filename} {row.note}", query),
                            "rank": _fallback_rank(f"{row.original_filename} {row.note}", query),
                            "contract_id": None})

    results.sort(key=lambda r: r["rank"], reverse=True)
    results = results[:limit]
    counts = {}
    for r in results:
        counts[r["type"]] = counts.get(r["type"], 0) + 1
    return {"query": query, "count": len(results), "counts": counts, "results": results}
