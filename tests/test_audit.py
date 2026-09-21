"""Phase 11 tests — append-only audit integrity + full lifecycle coverage."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from audit.models import AuditEvent
from contracts.models import Contract
from deadlines.models import Deadline
from obligations.models import Obligation
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email="au@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    return {"user": user, "ws": ws}


def test_rows_immutable_and_undeletable(setup):
    ev = AuditEvent.objects.create(
        actor=setup["user"], workspace=setup["ws"], entity_type="contract",
        entity_id="x", action="contract.created",
    )
    ev.action = "tampered"
    with pytest.raises(ValueError):
        ev.save()
    with pytest.raises(ValueError):
        ev.delete()
    assert AuditEvent.objects.get(pk=ev.pk).action == "contract.created"


def test_api_allows_only_read(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    ev = AuditEvent.objects.create(
        actor=setup["user"], workspace=setup["ws"], entity_type="contract",
        entity_id="x", action="contract.created",
    )
    assert client.post("/api/v1/audit/", {}, format="json").status_code == 405
    assert client.put(f"/api/v1/audit/{ev.id}/", {}, format="json").status_code == 405
    assert client.patch(f"/api/v1/audit/{ev.id}/", {}, format="json").status_code == 405
    assert client.delete(f"/api/v1/audit/{ev.id}/").status_code == 405
    assert client.get(f"/api/v1/audit/{ev.id}/").status_code == 200


def test_full_lifecycle_action_coverage(setup):
    """Upload → process → extract → review → deadline → risk → comment → evidence."""
    import fitz

    client = APIClient()
    client.force_authenticate(user=setup["user"])
    contract_id = client.post("/api/v1/contracts/", {
        "workspace": str(setup["ws"].id), "title": "Lifecycle Co",
        "status": "ACTIVE", "renewal_date": "2027-06-01",
    }, format="json").json()["id"]
    contract = Contract.objects.get(pk=contract_id)

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "The Vendor shall maintain insurance at all times during the term.")
    data = bytes(doc.tobytes())
    doc.close()
    f = SimpleUploadedFile("life.pdf", data, content_type="application/pdf")
    doc_id = client.post("/api/v1/documents/", {"contract": str(contract.id), "file": f}, format="multipart").json()["id"]

    ob = Obligation.objects.filter(contract=contract).first()
    assert ob is not None
    client.post(f"/api/v1/obligations/{ob.id}/confirm/")
    client.post("/api/v1/deadlines/generate/", {"contract": str(contract.id)}, format="json")
    client.post("/api/v1/risks/assess/", {"contract": str(contract.id)}, format="json")
    client.post("/api/v1/comments/", {"obligation": str(ob.id), "body": "noted"}, format="json")
    cert = SimpleUploadedFile("c.pdf", b"%PDF-1.4 cert", content_type="application/pdf")
    client.post("/api/v1/evidence/", {"obligation": str(ob.id), "file": cert}, format="multipart")

    actions = set(AuditEvent.objects.filter(workspace=setup["ws"]).values_list("action", flat=True))
    expected = {
        "contract.created", "document.uploaded", "document.processing_started",
        "document.processed", "contract.document_processed", "document.clauses_extracted",
        "document.obligations_extracted", "obligation.created", "obligation.confirmed",
        "contract.deadlines_generated", "contract.risk_assessed", "comment.created", "evidence.added",
    }
    missing = expected - actions
    assert not missing, f"missing audit actions: {missing}"

    # Every record carries actor/workspace/entity/timestamp.
    for ev in AuditEvent.objects.filter(workspace=setup["ws"]):
        assert ev.entity_type and ev.entity_id and ev.action and ev.created_at
