"""Rule-based obligation extractor — deterministic, evidence-bound.

Only creates obligations from clause text containing obligation language
(modal verbs / agreement verbs). Never invents text: source_text is always the
verbatim clause text.
"""
from __future__ import annotations

import re

OBLIGATION_RE = re.compile(
    r"\b(shall|must|will|agrees?\s+to|is\s+required\s+to|are\s+required\s+to|responsible\s+for|covenants?\s+to)\b",
    re.IGNORECASE,
)

ACTOR_RES = [
    re.compile(r"\b[Tt]he\s+(Vendor|Supplier|Contractor|Client|Company|Provider|Customer|Licensee|Licensor)\b"),
    re.compile(r"\b(Vendor|Supplier|Contractor|Client|Company|Provider|Customer)\s+(shall|must|will|agrees)\b"),
]

FREQUENCY_RES: list[tuple[str, str]] = [
    ("MONTHLY", r"\bmonthly\b"),
    ("QUARTERLY", r"\bquarterly\b"),
    ("SEMI_ANNUAL", r"\bsemi-annual\b|\bevery six months\b"),
    ("ANNUAL", r"\bannual(ly)?\b|\byearly\b|\bper year\b"),
    ("WEEKLY", r"\bweekly\b"),
    ("DAILY", r"\bdaily\b"),
    ("CONTINUOUS", r"\bthroughout the term\b|\bentire term\b|\bat all times\b|\bmaintain\b"),
]

NOTICE_RES = re.compile(r"\b(\d+)\s+days?(\s+business)?\s+(notice|prior|before|advance)\b", re.IGNORECASE)

EVIDENCE_BY_TYPE = {
    "INSURANCE": "insurance certificate",
    "PAYMENT": "payment receipt / invoice",
    "REPORTING": "report copy",
    "RENEWAL_NOTICE": "renewal notice record",
    "TERMINATION_NOTICE": "termination notice record",
    "COMPLIANCE": "compliance attestation",
    "SLA": "SLA performance report",
    "SECURITY": "security attestation (e.g. SOC 2)",
    "AUDIT": "audit report",
    "DELIVERY": "delivery confirmation",
    "CONFIDENTIALITY": "confidentiality acknowledgement",
}

CLAUSE_TO_OBLIGATION = {
    "INSURANCE": "INSURANCE",
    "PAYMENT": "PAYMENT",
    "REPORTING": "REPORTING",
    "RENEWAL": "RENEWAL_NOTICE",
    "TERMINATION": "TERMINATION_NOTICE",
    "COMPLIANCE": "COMPLIANCE",
    "SLA": "SLA",
    "CONFIDENTIALITY": "CONFIDENTIALITY",
    "SECURITY": "SECURITY",
    "AUDIT": "AUDIT",
    "DELIVERY": "DELIVERY",
    "NOTICE": "GENERAL",
    "LIABILITY": "GENERAL",
    "INDEMNIFICATION": "GENERAL",
    "DEFINITIONS": None,  # definitions state facts; they bind no party
    "GENERAL": "GENERAL",
}


def has_obligation_language(text: str) -> bool:
    return bool(OBLIGATION_RE.search(text))


def extract_actor(text: str) -> str:
    for rx in ACTOR_RES:
        m = rx.search(text)
        if m:
            return m.group(1).capitalize()
    if re.search(r"\beither party\b", text, re.IGNORECASE):
        return "Either party"
    return ""


def extract_frequency(text: str) -> str:
    for freq, pattern in FREQUENCY_RES:
        if re.search(pattern, text, re.IGNORECASE):
            return freq
    if NOTICE_RES.search(text):
        return "ONE_TIME"
    return "ONE_TIME"


def extract_action(text: str) -> str:
    """Deterministic action: modal verb + following words (max 14), cleaned."""
    m = OBLIGATION_RE.search(text)
    if not m:
        return text[:140].strip()
    tail = text[m.start():].strip()
    words = re.split(r"\s+", tail)
    action = " ".join(words[:14]).strip().rstrip(".,;:")
    return action[:280]


def build_obligation_fields(clause_type: str, heading: str, text: str) -> dict | None:
    """Return normalized obligation fields, or None if no obligation present."""
    obligation_type = CLAUSE_TO_OBLIGATION.get(clause_type)
    if obligation_type is None:
        return None
    if not has_obligation_language(text):
        return None
    actor = extract_actor(text)
    frequency = extract_frequency(text)
    action = extract_action(text)
    title_bits = [t for t in [actor, action[:90]] if t]
    title = " — ".join(title_bits) if title_bits else text[:120].strip()
    return {
        "obligation_type": obligation_type,
        "actor": actor,
        "action": action,
        "requirement": (heading or "")[:500],
        "frequency": frequency,
        "evidence_required": EVIDENCE_BY_TYPE.get(obligation_type, ""),
        "title": title[:300],
    }
