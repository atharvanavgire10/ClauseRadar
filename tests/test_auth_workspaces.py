"""Phase 01 tests — auth, tenant isolation, contracts, audit foundation."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from audit.models import AuditEvent
from contracts.models import Contract
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


@pytest.fixture
def user_a(db):
    return User.objects.create_user(email="a@example.com", password="password123")


@pytest.fixture
def user_b(db):
    return User.objects.create_user(email="b@example.com", password="password123")


def make_org_workspace(user, org_name="Acme", ws_name="Legal"):
    org = Organization.objects.create(name=org_name, created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name=ws_name, created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    return org, ws


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_register_login_me_flow(db):
    client = APIClient()
    r = client.post("/api/v1/auth/register/", {"email": "new@example.com", "password": "password123"}, format="json")
    assert r.status_code == 201, r.content
    assert "token" in r.json()

    client2 = APIClient()
    r2 = client2.post("/api/v1/auth/login/", {"email": "new@example.com", "password": "password123"}, format="json")
    assert r2.status_code == 200
    token = r2.json()["token"]

    client3 = APIClient(HTTP_AUTHORIZATION=f"Token {token}")
    r3 = client3.get("/api/v1/auth/me/")
    assert r3.status_code == 200
    assert r3.json()["email"] == "new@example.com"


def test_duplicate_registration_rejected(db, user_a):
    client = APIClient()
    r = client.post("/api/v1/auth/register/", {"email": "a@example.com", "password": "password123"}, format="json")
    assert r.status_code == 400


def test_unauthenticated_contract_list_denied(db):
    client = APIClient()
    assert client.get("/api/v1/contracts/").status_code in (401, 403)


def test_workspace_isolation_between_users(db, user_a, user_b):
    _, ws_a = make_org_workspace(user_a, "OrgA", "WSA")
    _, ws_b = make_org_workspace(user_b, "OrgB", "WSB")

    ca = auth_client(user_a)
    cb = auth_client(user_b)

    # A creates a contract in own workspace
    r = ca.post("/api/v1/contracts/", {"workspace": str(ws_a.id), "title": "Vendor Agreement", "status": "DRAFT"}, format="json")
    assert r.status_code == 201, r.content
    contract_id = r.json()["id"]

    # A sees it; B does not
    assert len(ca.get("/api/v1/contracts/").json()["results"]) == 1
    assert len(cb.get("/api/v1/contracts/").json()["results"]) == 0

    # B cannot fetch A's contract directly
    assert cb.get(f"/api/v1/contracts/{contract_id}/").status_code == 404

    # B cannot create in A's workspace
    r2 = cb.post("/api/v1/contracts/", {"workspace": str(ws_a.id), "title": "Intrusion"}, format="json")
    assert r2.status_code in (400, 403, 404)

    # Cross-workspace contract in B's workspace invisible to A
    assert ca.get("/api/v1/contracts/").json()["count"] == 1


def test_contract_validation_end_before_start(db, user_a):
    _, ws = make_org_workspace(user_a)
    client = auth_client(user_a)
    r = client.post(
        "/api/v1/contracts/",
        {"workspace": str(ws.id), "title": "Bad dates", "start_date": "2026-05-01", "end_date": "2026-04-01"},
        format="json",
    )
    assert r.status_code == 400


def test_audit_created_and_read_only(db, user_a):
    org, ws = make_org_workspace(user_a)
    client = auth_client(user_a)
    client.post("/api/v1/contracts/", {"workspace": str(ws.id), "title": "Audited Agreement"}, format="json")
    assert AuditEvent.objects.filter(workspace=ws, action="contract.created").exists()

    # Audit list visible
    r = client.get(f"/api/v1/audit/?workspace={ws.id}")
    assert r.status_code == 200
    assert r.json()["count"] >= 1

    # Append-only: no POST/DELETE
    assert client.post("/api/v1/audit/", {}, format="json").status_code == 405
    first = AuditEvent.objects.filter(workspace=ws).first()
    assert client.delete(f"/api/v1/audit/{first.id}/").status_code == 405


def test_viewer_cannot_create_contract(db, user_a, user_b):
    _, ws = make_org_workspace(user_a)
    WorkspaceMembership.objects.create(workspace=ws, user=user_b, role="VIEWER")
    OrganizationMembership.objects.create(organization=ws.organization, user=user_b, role="MEMBER")
    cb = auth_client(user_b)
    # viewer can read (empty or visible)
    assert cb.get("/api/v1/contracts/").status_code == 200
    r = cb.post("/api/v1/contracts/", {"workspace": str(ws.id), "title": "Nope"}, format="json")
    assert r.status_code in (400, 403)


def test_organization_crud_scoped(db, user_a, user_b):
    make_org_workspace(user_a, "OrgA", "WSA")
    make_org_workspace(user_b, "OrgB", "WSB")
    ca = auth_client(user_a)
    names = [o["name"] for o in ca.get("/api/v1/organizations/").json()["results"]]
    assert "OrgA" in names and "OrgB" not in names
