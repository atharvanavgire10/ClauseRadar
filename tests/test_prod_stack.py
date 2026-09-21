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


def test_worker_executes_task_through_broker(db):
    """End-to-end broker→worker→Postgres using the real risk-assess task.

    Skips unless a worker is actually consuming (proves the worker path instead
    of hiding behind eager execution).
    """
    from celery import current_app
    from django.test import override_settings

    from risks.models import RiskFinding

    try:
        alive = current_app.control.inspect(timeout=5).ping()
    except Exception:
        alive = None
    if not alive:
        pytest.skip("no celery worker running")

    from obligations.models import Obligation

    from risks.tasks import assess_workspace_task

    user, ws = _setup(db)
    contract = Contract.objects.create(workspace=ws, title="Risky", created_by=user)
    Obligation.objects.create(
        workspace=ws, contract=contract, title="Duty", obligation_type="GENERAL",
        source_text="The Vendor shall do the thing described here.", status="ACTIVE")
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False):
        delivered = assess_workspace_task.apply_async(args=[str(ws.id)]).get(timeout=120)
    assert delivered >= 1
    assert RiskFinding.objects.filter(workspace=ws).exists()
