"""Deterministic clause classifier — keyword/regex rules, no LLM.

Every rule is transparent and unit-tested. Returns (clause_type, confidence).
"""
from __future__ import annotations

import re

# Each category maps to weighted regex patterns (case-insensitive).
RULES: dict[str, list[str]] = {
    "DEFINITIONS": [r"\bmeans\b.{0,40}\bfor purposes of\b", r"\b\"[A-Z][\w ]+\"\s+means\b", r"\bdefinitions?\b.{0,20}:", r"\bshall have the meaning\b"],
    "PAYMENT": [r"\binvoice\b", r"\bpayment (terms|due|schedule)\b", r"\bnet \d+ days?\b", r"\bpay (within|no later than)\b", r"\blate fee\b", r"\bfees?\b.{0,30}\bdue\b"],
    "RENEWAL": [r"\brenew(al)?\b", r"\bauto-?renew", r"\brenewal term\b", r"\bextend.{0,20}term\b", r"\bnotice of (non-?)?renewal\b"],
    "TERMINATION": [r"\bterminat\w*\b", r"\bterminate\b.{0,30}\b(for convenience|for cause)\b", r"\btermination for\b", r"\bnotice of termination\b"],
    "INSURANCE": [r"\binsurance\b", r"\binsured\b", r"\bcertificate of insurance\b", r"\bcoverage\b.{0,30}\b(liability|cyber|property)\b", r"\bpolicy\b.{0,20}\binsurance\b"],
    "CONFIDENTIALITY": [r"\bconfidential\b", r"\bnon-?disclosure\b", r"\bproprietary information\b", r"\bNDA\b"],
    "SECURITY": [r"\binformation security\b", r"\bcyber(security)?\b", r"\bdata (breach|protection|security)\b", r"\bSOC\s?2\b", r"\bISO\s?27001\b", r"\bencryption\b"],
    "COMPLIANCE": [r"\bcompli\w+\b.{0,20}\b(laws?|regulations?)\b", r"\bapplicable law\b", r"\bregulatory\b", r"\bGDPR\b", r"\bHIPAA\b", r"\banti-?corruption\b"],
    "SLA": [r"\bservice level\b", r"\bSLA\b", r"\buptime\b.{0,20}\d", r"\bresponse time\b", r"\bservice credits?\b"],
    "REPORTING": [r"\breport(s|ing)?\b.{0,30}\b(monthly|quarterly|annual|deliver)\b", r"\bprovide.{0,20}reports?\b", r"\bdeliverables?\b"],
    "AUDIT": [r"\bright to audit\b", r"\baudit (rights?|trail|logs?)\b", r"\binspect.{0,20}(books|records)\b"],
    "LIABILITY": [r"\blimitation of liability\b", r"\bliab\w*\b.{0,20}\b(cap|exceed|limited)\b", r"\bconsequential damages\b", r"\bcap\b.{0,20}\bliability\b"],
    "INDEMNIFICATION": [r"\bindemnif\w+\b", r"\bhold harmless\b", r"\bdefend\b.{0,30}\b(claims?|against)\b"],
    "NOTICE": [r"\bnotices?\b.{0,30}\b(written|delivered|address)\b", r"\bnotice period\b", r"\bnotify\b.{0,30}\b(days?|writing)\b"],
    "DELIVERY": [r"\bdeliver(y|ables?)\b", r"\bdelivery (date|schedule|timeline)\b", r"\bship(ment|ping)?\b", r"\bmilestone\b"],
}

_COMPILED: dict[str, list] = {k: [re.compile(p, re.IGNORECASE) for p in v] for k, v in RULES.items()}

# A paragraph that looks like a section heading (short, ends with colon, numbered, or ALLCAPS).
HEADING_RE = re.compile(r"^(section\s+\d+|article\s+\d+|[A-Z][\w ,&'\-()]{2,80}:|[A-Z][A-Z0-9 ,&'\-()]{4,80})$")


def classify(text: str) -> tuple[str, float]:
    """Classify clause text. Returns (clause_type, confidence in 0..1)."""
    scores: dict[str, int] = {}
    for category, patterns in _COMPILED.items():
        hits = sum(1 for rx in patterns if rx.search(text))
        if hits:
            scores[category] = hits
    if not scores:
        return "GENERAL", 0.35
    best = max(scores, key=lambda k: scores[k])
    hits = scores[best]
    total_patterns = len(RULES[best])
    confidence = round(min(0.95, 0.55 + 0.12 * (hits - 1) + 0.05 * (hits / total_patterns)), 2)
    # Tie-break deterministically: first category in RULES order wins (dict order stable).
    return best, confidence


def looks_like_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 100:
        return False
    return bool(HEADING_RE.match(line))


def segment_page(page_text: str) -> list[tuple[str, str, int, int]]:
    """Split page text into (heading, text, start_offset, end_offset) candidates.

    Blocks are split on blank lines; a short heading-like line preceding a block
    becomes its heading. Blocks under 40 chars are merged into the next block
    (they are usually fragments/headers/footers) unless nothing follows.
    """
    if not page_text or not page_text.strip():
        return []
    raw_blocks = re.split(r"\n\s*\n", page_text)
    # Compute offsets by scanning.
    segments: list[tuple[str, str, int, int]] = []
    cursor = 0
    pending_heading = ""
    pending_short: list[tuple[str, int]] = []  # (text, offset)
    for block in raw_blocks:
        stripped = block.strip()
        if not stripped:
            cursor += len(block) + 2
            continue
        start = page_text.find(stripped, cursor)
        if start < 0:
            start = cursor
        end = start + len(stripped)
        cursor = end
        lines = stripped.splitlines()
        heading = ""
        body = stripped
        if len(lines) > 1 and looks_like_heading(lines[0]):
            heading = lines[0].strip().rstrip(":")
            body = "\n".join(lines[1:]).strip()
        elif pending_heading and len(stripped) >= 40:
            heading, pending_heading = pending_heading, ""
        elif looks_like_heading(stripped) and len(stripped) < 100:
            pending_heading = stripped.rstrip(":")
            continue
        if len(body) < 40:
            pending_short.append((body, start))
            continue
        if pending_short:
            first_text, first_start = pending_short[0]
            body = " ".join([t for t, _ in pending_short] + [body])
            start = first_start
            end = start + len(body)
            pending_short = []
        segments.append((heading, body, start, end))
    if pending_short:
        body = " ".join(t for t, _ in pending_short)
        if len(body) >= 20:
            segments.append(("", body, pending_short[0][1], pending_short[0][1] + len(body)))
    return segments
