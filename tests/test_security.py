"""Phase 18 tests — cross-workspace isolation on EVERY endpoint, headers, errors."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from audit.models import AuditEvent
from clauses.models import Clause
from contracts.models import Contract, ContractVersion
from deadlines.models import Deadline
from documents.models import Document
from notifications.models import Notification
from obligations.models import Obligation
from organizations.models import Organization, OrganizationMembership
from risks.models import RiskFinding
from workflows.models import Comment, Evidence, Task
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


@pytest.fixture
def two_tenants(db):
    users = {}
    data = {}
    for key, email in (("a", "t1a@example.com"), ("b", "t1b@example.com")):
        user = User.objects.create_user(email=email, password="password123")
        users[key] = user
        org = Organization.objects.create(name=f"Org-{key}", created_by=user)
        OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
        ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
        WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
        contract = Contract.objects.create(workspace=ws, title=f"Contract-{key}", created_by=user)
        data[key] = {"user": user, "ws": ws, "contract": contract}
    # Tenant A objects across every domain model.
    a = data["a"]
    doc = Document.objects.create(
        workspace=a["ws"], contract=a["contract"], file="t/a.pdf", original_filename="a.pdf",
        mime="application/pdf", size_bytes=3, sha256="aaa", status="READY")
    clause = Clause.objects.create(
        workspace=a["ws"], contract=a["contract"], document=doc, page_number=1,
        text="The Vendor shall maintain insurance at all times here.", clause_type="INSURANCE")
    ob = Obligation.objects.create(
        workspace=a["ws"], contract=a["contract"], document=doc, clause=clause,
        title="Duty", obligation_type="INSURANCE", source_text="x", status="ACTIVE")
    dl = Deadline.objects.create(
        workspace=a["ws"], contract=a["contract"], obligation=ob, title="D",
        kind="FIXED", due_date="2027-01-01", rule="test")
    risk = RiskFinding.objects.create(
        workspace=a["ws"], contract=a["contract"], obligation=ob, rule="no_owner",
        points=7, severity="LOW", title="T", explanation="E")
    comment = Comment.objects.create(workspace=a["ws"], obligation=ob, body="hi")
    ev = Evidence.objects.create(
        workspace=a["ws"], obligation=ob, file="t/e.pdf", original_filename="e.pdf",
        mime="application/pdf", size_bytes=3, sha256="eee")
    task = Task.objects.create(workspace=a["ws"], contract=a["contract"], title="T")
    version = ContractVersion.objects.create(contract=a["contract"], version_number=1)
    notif = Notification.objects.create(workspace=a["ws"], user=a["user"], kind="risk_increased", title="R")
    audit = AuditEvent.objects.create(
        actor=a["user"], workspace=a["ws"], entity_type="contract",
        entity_id=str(a["contract"].id), action="contract.created")
    a.update({"doc": doc, "clause": clause, "ob": ob, "dl": dl, "risk": risk,
              "comment": comment, "ev": ev, "task": task, "version": version,
              "notif": notif, "audit": audit})
    return data


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def test_no_cross_workspace_reads(two_tenants):
    b = client_for(two_tenants["b"]["user"])
    a = two_tenants["a"]
    probes = [
        f"/api/v1/contracts/{a['contract'].id}/",
        f"/api/v1/documents/{a['doc'].id}/",
        f"/api/v1/documents/{a['doc'].id}/download/",
        f"/api/v1/documents/{a['doc'].id}/pages/",
        f"/api/v1/clauses/{a['clause'].id}/",
        f"/api/v1/obligations/{a['ob'].id}/",
        f"/api/v1/deadlines/{a['dl'].id}/",
        f"/api/v1/risks/{a['risk'].id}/",
        f"/api/v1/comments/{a['comment'].id}/",
        f"/api/v1/evidence/{a['ev'].id}/",
        f"/api/v1/evidence/{a['ev'].id}/download/",
        f"/api/v1/tasks/{a['task'].id}/",
        f"/api/v1/contracts/{a['contract'].id}/versions/",
        f"/api/v1/audit/{a['audit'].id}/",
        f"/api/v1/notifications/{a['notif'].id}/",
    ]
    for url in probes:
        assert b.get(url).status_code == 404, url


def test_no_cross_workspace_writes(two_tenants):
    b = client_for(two_tenants["b"]["user"])
    a = two_tenants["a"]
    assert b.post(f"/api/v1/obligations/{a['ob'].id}/confirm/").status_code == 404
    assert b.post(f"/api/v1/obligations/{a['ob'].id}/assign/", {"email": "t1b@example.com"}, format="json").status_code == 404
    assert b.post(f"/api/v1/deadlines/{a['dl'].id}/complete/").status_code == 404
    # Custom actions deny cross-workspace access (403 or 404 — both safe, never 2xx).
    assert b.post(f"/api/v1/clauses/extract/", {"document": str(a["doc"].id)}, format="json").status_code in (403, 404)
    assert b.post(f"/api/v1/risks/assess/", {"contract": str(a["contract"].id)}, format="json").status_code in (403, 404)
    assert b.delete(f"/api/v1/documents/{a['doc'].id}/").status_code == 404
    assert b.delete(f"/api/v1/tasks/{a['task'].id}/").status_code == 404


def test_list_endpoints_never_leak(two_tenants):
    b = client_for(two_tenants["b"]["user"])
    # Tenant B sees exactly its own contract and nothing else.
    contracts = b.get("/api/v1/contracts/").json()
    assert contracts["count"] == 1
    assert contracts["results"][0]["title"] == "Contract-b"
    for url in ("/api/v1/documents/", "/api/v1/clauses/",
                "/api/v1/obligations/", "/api/v1/deadlines/", "/api/v1/risks/",
                "/api/v1/comments/", "/api/v1/evidence/", "/api/v1/tasks/",
                "/api/v1/audit/", "/api/v1/notifications/"):
        assert b.get(url).json()["count"] == 0, url
    search = b.get("/api/v1/search/?q=Contract").json()
    assert all(h["title"] != "Contract-a" for h in search["results"])


def test_unauthenticated_file_access_denied(two_tenants):
    anon = APIClient()
    a = two_tenants["a"]
    assert anon.get(f"/api/v1/documents/{a['doc'].id}/download/").status_code in (401, 403)
    assert anon.get(f"/api/v1/evidence/{a['ev'].id}/download/").status_code in (401, 403)
    assert anon.get("/api/v1/contracts/").status_code in (401, 403)


def test_security_headers_present(two_tenants):
    r = client_for(two_tenants["a"]["user"]).get("/api/v1/contracts/")
    assert r["X-Content-Type-Options"] == "nosniff"
    assert r["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in r


def test_error_envelope_never_leaks_tracebacks(two_tenants):
    b = client_for(two_tenants["b"]["user"])
    r = b.post("/api/v1/contracts/", {"title": ""}, format="json")
    assert r.status_code == 400
    body = r.json()
    assert "detail" in body and "Traceback" not in str(body)
    r = b.get("/api/v1/contracts/00000000-0000-0000-0000-000000000000/")
    assert r.status_code == 404
    assert "Traceback" not in str(r.json())
