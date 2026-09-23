"""CSRF regression tests — browser semantics, not token-client semantics.

Production bug: the SPA never sent a CSRF token, so any browser carrying a
Django session cookie (register/login plants one; same-origin deployment
sends it on every request) got `403 CSRF Failed` on every POST — including
the public `eval/session` bootstrap itself. Fresh anonymous browsers worked,
which is why token-only tests never caught it.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from contracts.models import Contract
from obligations.models import Obligation
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email="csrf@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    contract = Contract.objects.create(workspace=ws, title="MSA", created_by=user)
    ob = Obligation.objects.create(
        workspace=ws, contract=contract, title="Duty", obligation_type="GENERAL",
        source_text="The Vendor shall do the thing.", status="NEEDS_REVIEW")
    return {"user": user, "ob": ob}


def test_eval_session_anonymous_needs_no_csrf(setup):
    """Fresh browser (no cookies): public bootstrap works token-free."""
    assert APIClient().post("/api/v1/eval/session/").status_code == 200


def test_eval_info_sets_csrf_cookie(setup):
    """Landing bootstrap endpoint plants a readable csrftoken cookie."""
    r = APIClient().get("/api/v1/eval/info/")
    assert r.status_code == 200
    assert "csrftoken" in r.cookies


def test_eval_session_with_stale_session_requires_csrf(setup):
    """Exact production bug: session cookie present, no token → 403 CSRF;
    same request with the cookie's token → 200."""
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(setup["user"])
    assert client.post("/api/v1/eval/session/").status_code == 403

    client.get("/api/v1/eval/info/")
    token = client.cookies["csrftoken"].value
    r = client.post("/api/v1/eval/session/", HTTP_X_CSRFTOKEN=token)
    assert r.status_code == 200, r.content


def test_session_mutation_csrf_protected_and_working(setup):
    """Protection stays on for session clients; the token flow succeeds."""
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(setup["user"])
    url = f"/api/v1/obligations/{setup['ob'].id}/confirm/"
    assert client.post(url).status_code == 403
    client.get("/api/v1/eval/info/")
    token = client.cookies["csrftoken"].value
    assert client.post(url, HTTP_X_CSRFTOKEN=token).status_code == 200
