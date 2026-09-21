"""Phase 20 tests — deployment contract: health/ready, prod guards, scheduler."""
import pytest
from django.conf import settings
from rest_framework.test import APIClient


def test_health_shape():
    r = APIClient().get("/api/health/")
    assert r.status_code == 200
    assert set(r.json()) >= {"status", "service", "version"}


@pytest.mark.django_db
def test_ready_shape_reports_db_and_ai():
    r = APIClient().get("/api/ready/")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["checks"]["database"] == "ok"
    assert "ai_provider" in body


def test_prod_hardening_present():
    assert "core.middleware.SecurityHeadersMiddleware" in settings.MIDDLEWARE
    assert settings.STATIC_ROOT is not None
    tasks = {v["task"] for v in settings.CELERY_BEAT_SCHEDULE.values()}
    assert "deadlines.generate_recurring" in tasks
    assert "notifications.deadline_scan" in tasks


def test_throttle_scopes_include_eval():
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert rates["eval_session"] == "30/hour"
    assert rates["eval_reset"] == "10/hour"
    assert rates["ai_burst"] == "60/hour"


def test_dev_secret_refused_when_debug_false():
    """Production safety model: default key + DEBUG=False must fail at import."""
    import os
    import subprocess
    import sys

    backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
    env = {**os.environ, "DJANGO_DEBUG": "False"}
    env.pop("DJANGO_SECRET_KEY", None)
    proc = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=backend_dir, capture_output=True, text=True, env=env, timeout=120,
    )
    assert proc.returncode != 0
    assert "SECRET_KEY" in proc.stderr
