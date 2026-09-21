"""Deterministic version comparison — difflib alignment, no LLM.

Change kinds: ADDED | REMOVED | MODIFIED | UNCHANGED.
"""
from __future__ import annotations

import difflib
import re

MATCH_THRESHOLD = 0.85

IMPACT_NOTES = {
    "PAYMENT": "Payment terms changed — verify payment deadlines and amounts.",
    "RENEWAL": "Renewal terms changed — verify renewal date and notice deadlines.",
    "TERMINATION": "Termination terms changed — verify notice periods.",
    "INSURANCE": "Insurance requirements changed — verify coverage obligations.",
    "LIABILITY": "Liability allocation changed — re-assess risk.",
    "INDEMNIFICATION": "Indemnification changed — re-assess risk.",
    "SLA": "Service levels changed — verify SLA deadlines.",
    "CONFIDENTIALITY": "Confidentiality scope changed — verify handling duties.",
    "DELIVERY": "Delivery terms changed — verify delivery deadlines.",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


def split_sentences(text: str) -> list[str]:
    """Split text into sentences (≥30 chars kept). Deterministic."""
    parts = [s.strip() for s in SENTENCE_RE.split(text or "") if s and s.strip()]
    return [p for p in parts if len(p) >= 30]


def _sentence_fallback(removed: list[dict], added: list[dict]) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Align unmatched clauses at sentence level.

    Returns (modified, unchanged, removed_remainder, added_remainder) where
    modified/unchanged entries carry old/new sentence dicts plus parent ids.
    """
    removed_sents, added_sents = [], []
    for c in removed:
        for i, s in enumerate(split_sentences(c["text"])):
            removed_sents.append({"parent": c, "idx": i, "text": s})
    for c in added:
        for i, s in enumerate(split_sentences(c["text"])):
            added_sents.append({"parent": c, "idx": i, "text": s})
    modified, unchanged = [], []
    used_removed_parents, used_added_parents = set(), set()
    remaining_added = list(added_sents)
    for rs in removed_sents:
        best, best_ratio = None, 0.0
        for cand in remaining_added:
            ratio = difflib.SequenceMatcher(None, _normalize(rs["text"]), _normalize(cand["text"])).ratio()
            if ratio > best_ratio:
                best, best_ratio = cand, ratio
        if best is not None and best_ratio >= 0.80:
            remaining_added.remove(best)
            old = {**rs["parent"], "text": rs["text"], "id": f"{rs['parent']['id']}:s{rs['idx']}"}
            new = {**best["parent"], "text": best["text"], "id": f"{best['parent']['id']}:s{best['idx']}"}
            entry = {"old": old, "new": new, "similarity": round(best_ratio, 3)}
            if _normalize(rs["text"]) == _normalize(best["text"]):
                unchanged.append(entry)
            else:
                entry["impact"] = IMPACT_NOTES.get(
                    new["clause_type"] or old["clause_type"],
                    "Clause wording changed — review linked obligations.")
                modified.append(entry)
            used_removed_parents.add(rs["parent"]["id"])
            used_added_parents.add(best["parent"]["id"])
    removed_remainder = [c for c in removed if c["id"] not in used_removed_parents]
    added_remainder = [c for c in added if c["id"] not in used_added_parents]
    return modified, unchanged, removed_remainder, added_remainder


def compare_clause_lists(old: list[dict], new: list[dict]) -> dict:
    """Align two clause lists [{id, clause_type, heading, text, page_number}].

    Greedy best-match on normalized text ratio; matched pairs with ratio 1.0
    are UNCHANGED, >= threshold MODIFIED, else REMOVED + ADDED.
    """
    new_remaining = list(new)
    modified, unchanged, removed = [], [], []
    for o in old:
        best, best_ratio = None, 0.0
        for n in new_remaining:
            ratio = difflib.SequenceMatcher(None, _normalize(o["text"]), _normalize(n["text"])).ratio()
            # Same-type pairs match more readily (reworded clauses keep identity).
            if o["clause_type"] == n["clause_type"]:
                ratio = min(1.0, ratio + 0.05)
            if ratio > best_ratio:
                best, best_ratio = n, ratio
        if best is not None and best_ratio >= MATCH_THRESHOLD:
            new_remaining.remove(best)
            entry = {"old": o, "new": best, "similarity": round(best_ratio, 3)}
            if _normalize(o["text"]) == _normalize(best["text"]) and o["clause_type"] == best["clause_type"]:
                unchanged.append(entry)
            else:
                entry["impact"] = IMPACT_NOTES.get(best["clause_type"] or o["clause_type"], "Clause wording changed — review linked obligations.")
                modified.append(entry)
        else:
            removed.append(o)
    added = new_remaining
    # Sentence-level fallback for otherwise unmatched clauses (e.g. one edited
    # sentence on an otherwise identical page).
    s_mod, s_unch, removed, added = _sentence_fallback(removed, added)
    modified.extend(s_mod)
    unchanged.extend(s_unch)
    return {"added": added, "removed": removed, "modified": modified, "unchanged": unchanged,
            "counts": {"added": len(added), "removed": len(removed),
                       "modified": len(modified), "unchanged": len(unchanged)}}
