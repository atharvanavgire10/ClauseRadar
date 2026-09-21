"""Phase 13 tests — versioning, deterministic diff, affected obligations."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from contracts.diff import compare_clause_lists
from contracts.models import Contract, ContractVersion
from obligations.models import Obligation
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


def test_diff_detects_all_kinds():
    old = [
        {"id": "a", "clause_type": "PAYMENT", "heading": "", "text": "Invoices are due net 30 days from receipt.", "page_number": 1},
        {"id": "b", "clause_type": "GENERAL", "heading": "", "text": "The sky is blue on most days here.", "page_number": 1},
        {"id": "c", "clause_type": "NOTICE", "heading": "", "text": "Notices must be in writing always.", "page_number": 2},
    ]
    new = [
        {"id": "a2", "clause_type": "PAYMENT", "heading": "", "text": "Invoices are due net 15 days from receipt.", "page_number": 1},
        {"id": "c2", "clause_type": "NOTICE", "heading": "", "text": "Notices must be in writing always.", "page_number": 2},
        {"id": "d", "clause_type": "INSURANCE", "heading": "", "text": "The Vendor shall maintain insurance.", "page_number": 3},
    ]
    result = compare_clause_lists(old, new)
    assert result["counts"] == {"added": 1, "removed": 1, "modified": 1, "unchanged": 1}
    assert result["modified"][0]["old"]["text"].endswith("30 days from receipt.")
    assert result["modified"][0]["new"]["text"].endswith("15 days from receipt.")
    assert "impact" in result["modified"][0]


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email="vv@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    contract = Contract.objects.create(workspace=ws, title="Services MSA", created_by=user)
    return {"user": user, "ws": ws, "contract": contract}


def _pdf(texts):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for t in texts:
        page.insert_text((72, y), t)
        y += 30
    data = bytes(doc.tobytes())
    doc.close()
    return data


def test_upload_creates_versions_and_compare_detects_payment_change(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    cid = setup["contract"].id
    v1 = _pdf(["Invoices are due net 30 days from receipt of the invoice document.",
               "The Vendor shall maintain insurance at all times during the term."])
    v2 = _pdf(["Invoices are due net 15 days from receipt of the invoice document.",
               "The Vendor shall maintain insurance at all times during the term.",
               "The Vendor shall deliver monthly reports to the Client liaison."])
    f1 = SimpleUploadedFile("v1.pdf", v1, content_type="application/pdf")
    f2 = SimpleUploadedFile("v2.pdf", v2, content_type="application/pdf")
    assert client.post("/api/v1/documents/", {"contract": str(cid), "file": f1}, format="multipart").status_code == 201
    assert client.post("/api/v1/documents/", {"contract": str(cid), "file": f2}, format="multipart").status_code == 201

    versions = client.get(f"/api/v1/contracts/{cid}/versions/").json()
    assert [v["version_number"] for v in versions] == [1, 2]

    diff = client.get(f"/api/v1/contracts/{cid}/compare/?from=1&to=2").json()
    assert diff["counts"]["modified"] >= 1
    payment = [m for m in diff["modified"] if "30 days" in m["old"]["text"]]
    assert payment, diff["counts"]
    assert "15 days" in payment[0]["new"]["text"]
    assert payment[0]["impact"]
    assert "affected_obligations" in payment[0]
    # Affected obligations attached (v1 payment clause produced obligations).
    assert ContractVersion.objects.filter(contract_id=cid).count() == 2


def test_compare_missing_version_404(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    r = client.get(f"/api/v1/contracts/{setup['contract'].id}/compare/?from=1&to=9")
    assert r.status_code == 404
