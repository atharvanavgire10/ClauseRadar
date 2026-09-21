"""Phase 06 tests — verification history + invalid-transition guards."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from audit.models import AuditEvent
from contracts.models import Contract
from obligations.models import Obligation
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email="v@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    contract = Contract.objects.create(workspace=ws, title="Vendor Agreement", created_by=user)
    return {"user": user, "ws": ws, "contract": contract}


def test_extraction_history_queryable_per_obligation(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "The Vendor shall maintain insurance at all times during the term.")
    data = bytes(doc.tobytes())
    doc.close()
    f = SimpleUploadedFile("h.pdf", data, content_type="application/pdf")
    client.post("/api/v1/documents/", {"contract": str(setup["contract"].id), "file": f}, format="multipart")
    ob = Obligation.objects.filter(contract=setup["contract"]).first()
    client.post(f"/api/v1/obligations/{ob.id}/confirm/")

    r = client.get(f"/api/v1/audit/?entity_type=obligation&entity_id={ob.id}")
    assert r.status_code == 200
    actions = {e["action"] for e in r.json()["results"]}
    assert "obligation.created" in actions
    assert "obligation.confirmed" in actions


def test_reject_confirmed_is_invalid_transition(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    ob = Obligation.objects.create(
        workspace=setup["ws"], contract=setup["contract"], title="Manual",
        obligation_type="GENERAL", source_text="Manual entry.",
    )
    client.post(f"/api/v1/obligations/{ob.id}/confirm/")
    r = client.post(f"/api/v1/obligations/{ob.id}/reject/", {"reason": "x"}, format="json")
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_transition"
    assert AuditEvent.objects.filter(entity_id=str(ob.id), action="obligation.rejected").count() == 0
