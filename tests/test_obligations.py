"""Phase 05/06 tests — obligation extraction + human verification workflow."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from contracts.models import Contract
from obligations.extractor import build_obligation_fields
from obligations.models import Obligation
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


def test_insurance_sentence_structured():
    fields = build_obligation_fields(
        "INSURANCE", "",
        "The Vendor shall maintain valid cyber insurance throughout the term.",
    )
    assert fields is not None
    assert fields["obligation_type"] == "INSURANCE"
    assert fields["actor"] == "Vendor"
    assert "Maintain insurance" in fields["action"] or "maintain" in fields["action"].lower()
    assert fields["frequency"] == "CONTINUOUS"
    assert fields["evidence_required"] == "insurance certificate"


def test_definitions_produce_no_obligation():
    assert build_obligation_fields("DEFINITIONS", "", '"Vendor" means ACME Corp for purposes of this agreement.') is None


def test_no_modal_verb_no_obligation():
    assert build_obligation_fields("PAYMENT", "", "Payment terms are described in Exhibit A.") is None


def test_monthly_frequency_detected():
    fields = build_obligation_fields("REPORTING", "", "The Vendor shall deliver monthly reports to the Client.")
    assert fields is not None
    assert fields["frequency"] == "MONTHLY"


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email="o@example.com", password="password123")
    reviewer = User.objects.create_user(email="r@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    OrganizationMembership.objects.create(organization=org, user=reviewer, role="MEMBER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    WorkspaceMembership.objects.create(workspace=ws, user=reviewer, role="MEMBER")
    contract = Contract.objects.create(workspace=ws, title="Vendor Agreement", created_by=user)
    return {"user": user, "reviewer": reviewer, "ws": ws, "contract": contract}


def upload_pdf(client, contract_id, texts):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for t in texts:
        page.insert_text((72, y), t)
        y += 30
    data = bytes(doc.tobytes())
    doc.close()
    f = SimpleUploadedFile("c.pdf", data, content_type="application/pdf")
    return client.post("/api/v1/documents/", {"contract": str(contract_id), "file": f}, format="multipart")


def test_pipeline_creates_needs_review_obligations(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    r = upload_pdf(client, setup["contract"].id, [
        "The Vendor shall maintain valid cyber insurance throughout the term period here.",
        "The Vendor shall deliver monthly reports detailing service performance levels achieved.",
    ])
    assert r.status_code == 201, r.content
    obs = Obligation.objects.filter(contract=setup["contract"])
    assert obs.count() >= 1
    assert all(o.status == "NEEDS_REVIEW" for o in obs)
    first = obs.first()
    assert first.source_text  # evidence always present
    assert first.clause_id is not None
    assert first.extraction_method == "RULE"


def test_confirm_reject_workflow_with_reviewer_evidence(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    upload_pdf(client, setup["contract"].id, ["The Vendor shall maintain insurance at all times during the term."])
    ob = Obligation.objects.filter(contract=setup["contract"]).first()
    assert ob is not None

    # Reviewer sees exact source evidence before confirming
    detail = client.get(f"/api/v1/obligations/{ob.id}/").json()
    assert detail["source_text"] and detail["clause"] and detail["page_number"] >= 1

    r = client.post(f"/api/v1/obligations/{ob.id}/confirm/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "CONFIRMED"
    assert body["reviewer_email"] == "o@example.com"
    assert body["reviewed_at"]

    # Double-confirm rejected as invalid transition
    assert client.post(f"/api/v1/obligations/{ob.id}/confirm/").status_code == 400

    # Activate confirmed obligation
    assert client.post(f"/api/v1/obligations/{ob.id}/activate/").json()["status"] == "ACTIVE"

    # Second obligation → reject with reason
    upload_pdf(client, setup["contract"].id, ["The Client must pay within 30 days of invoice receipt date here."])
    ob2 = Obligation.objects.filter(contract=setup["contract"], status="NEEDS_REVIEW").first()
    r2 = client.post(f"/api/v1/obligations/{ob2.id}/reject/", {"reason": "Duplicate of manual entry."}, format="json")
    assert r2.status_code == 200
    assert r2.json()["status"] == "REJECTED"


def test_edit_before_confirm(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    upload_pdf(client, setup["contract"].id, ["The Vendor shall maintain insurance at all times during the term."])
    ob = Obligation.objects.filter(contract=setup["contract"]).first()
    r = client.patch(f"/api/v1/obligations/{ob.id}/", {"title": "Maintain cyber insurance (edited)", "actor": "Vendor"}, format="json")
    assert r.status_code == 200
    assert r.json()["title"] == "Maintain cyber insurance (edited)"
    assert Obligation.objects.get(pk=ob.id).status == "NEEDS_REVIEW"  # edit preserves review state


def test_obligation_isolation(setup):
    outsider = User.objects.create_user(email="out@example.com", password="password123")
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    upload_pdf(client, setup["contract"].id, ["The Vendor shall maintain insurance at all times during the term."])
    other = APIClient()
    other.force_authenticate(user=outsider)
    assert other.get("/api/v1/obligations/").json()["count"] == 0
