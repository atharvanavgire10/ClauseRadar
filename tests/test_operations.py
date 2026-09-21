"""Phase 10 tests — assignment, comments, evidence, tasks, lifecycle."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from audit.models import AuditEvent
from contracts.models import Contract
from obligations.models import Obligation
from organizations.models import Organization, OrganizationMembership
from risks.services import assess_contract_risks
from workflows.models import Comment, Evidence, Task
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


@pytest.fixture
def setup(db):
    owner = User.objects.create_user(email="w10o@example.com", password="password123")
    member = User.objects.create_user(email="w10m@example.com", password="password123")
    outsider = User.objects.create_user(email="w10x@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=owner)
    for u, role in ((owner, "OWNER"), (member, "MEMBER")):
        OrganizationMembership.objects.create(organization=org, user=u, role=role)
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=owner)
    for u, role in ((owner, "OWNER"), (member, "MEMBER")):
        WorkspaceMembership.objects.create(workspace=ws, user=u, role=role)
    contract = Contract.objects.create(workspace=ws, title="MSA", created_by=owner)
    ob = Obligation.objects.create(
        workspace=ws, contract=contract, title="Maintain insurance",
        obligation_type="INSURANCE", source_text="The Vendor shall maintain insurance.",
        status="ACTIVE", evidence_required="insurance certificate",
    )
    return {"owner": owner, "member": member, "outsider": outsider, "ws": ws,
            "contract": contract, "ob": ob}


def auth(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def test_full_lifecycle_with_audit(setup):
    client = auth(setup["owner"])
    ob_id = setup["ob"].id
    assert client.post(f"/api/v1/obligations/{ob_id}/start/").json()["status"] == "IN_PROGRESS"
    assert client.post(f"/api/v1/obligations/{ob_id}/complete/").json()["status"] == "COMPLETED"
    assert client.post(f"/api/v1/obligations/{ob_id}/reopen/").json()["status"] == "ACTIVE"
    assert client.post(f"/api/v1/obligations/{ob_id}/waive/", {"reason": "N/A"}, format="json").json()["status"] == "WAIVED"
    actions = set(AuditEvent.objects.filter(entity_type="obligation", entity_id=str(ob_id)).values_list("action", flat=True))
    assert {"obligation.started", "obligation.completed", "obligation.reopened", "obligation.waived"} <= actions


def test_invalid_lifecycle_rejected(setup):
    client = auth(setup["owner"])
    ob_id = setup["ob"].id  # ACTIVE
    assert client.post(f"/api/v1/obligations/{ob_id}/complete/").status_code == 200  # ACTIVE→COMPLETED ok
    assert client.post(f"/api/v1/obligations/{ob_id}/start/").status_code == 400  # COMPLETED→IN_PROGRESS invalid


def test_assign_owner_must_be_member(setup):
    client = auth(setup["owner"])
    ob_id = setup["ob"].id
    r = client.post(f"/api/v1/obligations/{ob_id}/assign/", {"email": "w10m@example.com"}, format="json")
    assert r.status_code == 200
    assert r.json()["owner_email"] == "w10m@example.com"
    assert AuditEvent.objects.filter(entity_id=str(ob_id), action="obligation.owner_changed").exists()
    # Outsider is not a member → 400, owner unchanged.
    r2 = client.post(f"/api/v1/obligations/{ob_id}/assign/", {"email": "w10x@example.com"}, format="json")
    assert r2.status_code == 400
    assert Obligation.objects.get(pk=ob_id).owner.email == "w10m@example.com"


def test_priority_and_notes_editable(setup):
    client = auth(setup["owner"])
    r = client.patch(f"/api/v1/obligations/{setup['ob'].id}/",
                     {"priority": "URGENT", "notes": "Call broker Monday."}, format="json")
    assert r.status_code == 200
    assert r.json()["priority"] == "URGENT" and r.json()["notes"] == "Call broker Monday."
    assert client.patch(f"/api/v1/obligations/{setup['ob'].id}/", {"priority": "NOPE"}, format="json").status_code == 400


def test_comments_thread_and_author_rules(setup):
    owner, member = auth(setup["owner"]), auth(setup["member"])
    ob_id = setup["ob"].id
    r = member.post("/api/v1/comments/", {"obligation": str(ob_id), "body": "Broker contacted."}, format="json")
    assert r.status_code == 201, r.content
    assert owner.get(f"/api/v1/comments/?obligation={ob_id}").json()["count"] == 1
    cid = r.json()["id"]
    # Member cannot edit owner's... actually member authored it; owner cannot edit member's comment.
    assert owner.patch(f"/api/v1/comments/{cid}/", {"body": "hijack"}, format="json").status_code == 403
    assert member.patch(f"/api/v1/comments/{cid}/", {"body": "Broker contacted twice."}, format="json").status_code == 200
    # Outsider sees nothing.
    assert auth(setup["outsider"]).get("/api/v1/comments/").json()["count"] == 0


def test_evidence_upload_clears_risk_finding(setup):
    client = auth(setup["owner"])
    before = assess_contract_risks(setup["contract"].id)
    assert any(f.rule == "evidence_missing" for f in before["findings"])
    pdf = SimpleUploadedFile("cert.pdf", b"%PDF-1.4 fake cert", content_type="application/pdf")
    r = client.post("/api/v1/evidence/", {"obligation": str(setup["ob"].id), "file": pdf, "note": "2026 cert"}, format="multipart")
    assert r.status_code == 201, r.content
    assert Evidence.objects.filter(obligation=setup["ob"]).exists()
    after = assess_contract_risks(setup["contract"].id)
    assert not any(f.rule == "evidence_missing" for f in after["findings"])
    # Junk upload rejected.
    bad = SimpleUploadedFile("evil.pdf", b"MZ executable", content_type="application/pdf")
    r2 = client.post("/api/v1/evidence/", {"obligation": str(setup['ob'].id), "file": bad}, format="multipart")
    assert r2.status_code == 400


def test_tasks_crud_and_isolation(setup):
    client = auth(setup["owner"])
    r = client.post("/api/v1/tasks/", {"contract": str(setup["contract"].id), "title": "Chase certificate",
                                       "assignee": str(setup["member"].id)}, format="json")
    assert r.status_code == 201, r.content
    tid = r.json()["id"]
    assert client.patch(f"/api/v1/tasks/{tid}/", {"status": "DONE"}, format="json").json()["status"] == "DONE"
    assert auth(setup["outsider"]).get("/api/v1/tasks/").json()["count"] == 0
    assert auth(setup["outsider"]).get(f"/api/v1/tasks/{tid}/").status_code == 404
