"""Phase 24 tests — Vercel-native deployment paths.

Local backends (SQLite, filesystem storage, eager Celery) keep working; every
Vercel behavior is env-selected and covered here.
"""
import json
import os

from core.vercel import is_vercel, vercel_env


def test_vercel_env_detection(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    assert is_vercel() is False
    assert vercel_env() is None
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "production")
    assert is_vercel() is True
    assert vercel_env() == "production"


def test_vercel_mode_off_by_default():
    from django.conf import settings

    assert settings.VERCEL_DEPLOYMENT is False
    assert settings.DOCUMENT_STORAGE_BACKEND == "local"
    assert settings.CRON_SECRET == ""


def _load_settings_with(env: dict) -> dict:
    import subprocess
    import sys

    backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
    merged = {**os.environ, **env}
    code = (
        "import os, django;"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings');"
        "django.setup();"
        "from django.conf import settings;"
        "print(settings.VERCEL_DEPLOYMENT);"
        "print(settings.DOCUMENT_STORAGE_BACKEND);"
        "print(settings.CSRF_TRUSTED_ORIGINS);"
        "print(settings.FRONTEND_URL)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=backend_dir, capture_output=True, text=True, env=merged, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.splitlines()


def test_vercel_env_selection():
    lines = _load_settings_with({
        "VERCEL_DEPLOYMENT": "True",
        "DOCUMENT_STORAGE_BACKEND": "vercel_blob",
        "CRON_SECRET": "s3cret",
        "FRONTEND_URL": "https://app.example.com",
        "CORS_ALLOWED_ORIGINS": "https://app.example.com",
    })
    assert lines[0] == "True"
    assert lines[1] == "vercel_blob"
    assert "https://app.example.com" in lines[2]  # CSRF follows CORS origins


def test_no_silent_sqlite_in_production():
    import subprocess
    import sys

    backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    env.update({
        "DJANGO_DEBUG": "False",
        "DJANGO_SECRET_KEY": "long-enough-test-secret-key-0123456789abcdef",
        "DJANGO_ALLOWED_HOSTS": "example.com",
    })
    proc = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=backend_dir, capture_output=True, text=True, env=env, timeout=120,
    )
    assert proc.returncode != 0
    assert "DATABASE_URL" in proc.stderr


def test_vercel_entrypoint_exports_wsgi_app():
    """api/index.py must expose a Django WSGI app using existing config only."""
    import importlib.util
    import subprocess
    import sys

    root = os.path.join(os.path.dirname(__file__), "..")
    code = (
        "import importlib.util;"
        f"spec = importlib.util.spec_from_file_location('vercel_api', {root!r} + '/api/index.py');"
        "mod = importlib.util.module_from_spec(spec);"
        "spec.loader.exec_module(mod);"
        "print(callable(mod.app))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root, capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "True"
