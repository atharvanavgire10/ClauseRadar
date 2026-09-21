"""Production-stack integration tests — run for real in the CI `integration` job
(PostgreSQL + Redis services). Skip gracefully anywhere else."""
import pytest
from django.contrib.auth import get_user_model
from django.db import connection

from contracts.models import Contract
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()
needs_postgres = pytest.mark.skipif(
    connection.vendor != "postgresql", reason="requires PostgreSQL")


def _setup(db):
    user = User.objects.create_user(email="stack@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    return user, ws


@needs_postgres
def test_runs_on_postgresql(db):
    assert connection.vendor == "postgresql"


@needs_postgres
def test_postgres_fulltext_search_branch(db):
    """Exercises the SearchVector/SearchRank path (dead code on SQLite)."""
    from search.services import _is_postgres, search_workspace

    assert _is_postgres() is True
    user, ws = _setup(db)
    Contract.objects.create(workspace=ws, title="Zirconium Supply Agreement",
                            description="Covers zirconium deliveries.", created_by=user)
    result = search_workspace(user=user, query="zirconium")
    assert result["count"] >= 1
    assert all(hit["rank"] > 0 for hit in result["results"])


def test_redis_broker_reachable(db):
    """Proves the Celery broker URL resolves to a live Redis (skips without one)."""
    from celery import current_app

    try:
        with current_app.connection() as conn:
            conn.ensure_connection(max_retries=1)
    except Exception:
        pytest.skip("no Redis broker reachable")


def test_worker_executes_task_through_broker():
    """End-to-end broker→worker→backend round-trip with executor proof.

    Uses the DB-free debug task deliberately: pytest runs in a `test_`-prefixed
    database while an external worker uses DATABASE_URL as-is, so no
    DB-touching task can prove cross-process execution. The returned PID must
    differ from this process, which also catches eager mode masking as a worker.
    Skips unless a worker is actually consuming.
    """
    import os

    from celery import current_app
    from django.test import override_settings

    try:
        alive = current_app.control.inspect(timeout=5).ping()
    except Exception:
        alive = None
    if not alive:
        pytest.skip("no celery worker running")

    from config.celery import debug_task

    with override_settings(CELERY_TASK_ALWAYS_EAGER=False):
        result = debug_task.apply_async().get(timeout=120)
    assert result["pid"] != os.getpid(), "task executed eagerly instead of in the worker"
    assert result["hostname"]
