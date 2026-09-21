"""Vercel environment detection — pure os.environ reads, no Django needed."""
from __future__ import annotations

import os


def is_vercel() -> bool:
    """True on any Vercel runtime (Vercel always sets VERCEL=1)."""
    return os.environ.get("VERCEL", "") == "1"


def vercel_env() -> str | None:
    """Vercel environment name: production | preview | development | None."""
    return os.environ.get("VERCEL_ENV")
