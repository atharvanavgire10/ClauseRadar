"""Vercel serverless entrypoint for the Django backend.

Vercel's Python runtime executes this file as a serverless function; the
exported WSGI `app` serves every route rewritten here from /api/*. All
product code lives in backend/ — this adapter only wires import paths and
settings, then reuses the existing WSGI application unchanged.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
