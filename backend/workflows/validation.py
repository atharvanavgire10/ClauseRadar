"""Evidence upload validation — PDFs, DOCX, and images via magic bytes."""
from __future__ import annotations

import os
from pathlib import Path

ALLOWED = {
    ".pdf": ("application/pdf", b"%PDF"),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
}


def sniff_evidence(filename: str, head: bytes) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        return None
    mime, magic = ALLOWED[ext]
    return mime if head.startswith(magic) else None


def sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "evidence").strip() or "evidence"
    base = "".join(c if (c.isalnum() or c in "._- ") else "_" for c in base).strip(" .")
    return base[:200] or "evidence"
