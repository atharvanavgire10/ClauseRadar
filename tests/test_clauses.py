"""Phase 04 tests — deterministic clause detection + source navigation."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from clauses.detector import classify, segment_page
from clauses.models import Clause
from contracts.models import Contract
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


def test_classify_insurance():
    t, conf = classify("The Vendor shall maintain valid cyber insurance throughout the term.")
    assert t == "INSURANCE"
    assert conf >= 0.5


def test_classify_payment():
    t, _ = classify("Payment terms: net 30 days from invoice date. Late fee of 1.5% applies.")
    assert t == "PAYMENT"


def test_classify_renewal_and_termination():
    assert classify("This agreement will auto-renew for successive one-year renewal terms.")[0] == "RENEWAL"
    assert classify("Either party may terminate for convenience with 30 days notice of termination.")[0] == "TERMINATION"


def test_classify_general_fallback():
    t, conf = classify("The parties agree to have lunch on Tuesdays.")
    assert t == "GENERAL"
    assert conf < 0.5


def test_segment_page_heading_and_offsets():
    text = "Payment Terms:\n\nInvoices are due net 30 days from receipt. Late fees apply after 60 days of delay."
    segs = segment_page(text)
    assert len(segs) == 1
    heading, body, start, end = segs[0]
    assert heading == "Payment Terms"
    assert text[start:end] == body or body in text


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email="c@example.com", password="password123")
    other = User.objects.create_user(email="d@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    contract = Contract.objects.create(workspace=ws, title="Vendor Agreement", created_by=user)
    return {"user": user, "other": other, "ws": ws, "contract": contract}


def make_pdf_bytes(paragraphs: list[str]) -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for p in paragraphs:
        page.insert_text((72, y), p)
        y += 30
    data = bytes(doc.tobytes())
    doc.close()
    return data


def test_upload_auto_extracts_clauses_with_source(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    pdf = make_pdf_bytes([
        "The Vendor shall maintain valid cyber insurance throughout the term.",
        "Payment terms: invoices are due net 30 days from receipt of invoice.",
    ])
    f = SimpleUploadedFile("agree.pdf", pdf, content_type="application/pdf")
    r = client.post("/api/v1/documents/", {"contract": str(setup["contract"].id), "file": f}, format="multipart")
    assert r.status_code == 201, r.content
    doc_id = r.json()["id"]
    clauses = Clause.objects.filter(document_id=doc_id)
    assert clauses.count() >= 1
    types = {c.clause_type for c in clauses}
    assert "INSURANCE" in types or "PAYMENT" in types
    c = clauses.first()
    assert c.page_id is not None and c.page_number >= 1  # source navigation
    assert c.confidence > 0 and c.extraction_method == "RULE"


def test_clause_list_filtered_and_isolated(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    pdf = make_pdf_bytes(["The Vendor shall maintain insurance at all times during the term period."])
    f = SimpleUploadedFile("a.pdf", pdf, content_type="application/pdf")
    client.post("/api/v1/documents/", {"contract": str(setup["contract"].id), "file": f}, format="multipart")

    r = client.get(f"/api/v1/clauses/?contract={setup['contract'].id}&clause_type=INSURANCE")
    assert r.status_code == 200
    assert r.json()["count"] >= 1

    other = APIClient()
    other.force_authenticate(user=setup["other"])
    assert other.get("/api/v1/clauses/").json()["count"] == 0


def test_extract_action_idempotent(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    pdf = make_pdf_bytes(["Confidential information shall not be disclosed to any third party whatsoever."])
    f = SimpleUploadedFile("b.pdf", pdf, content_type="application/pdf")
    doc_id = client.post("/api/v1/documents/", {"contract": str(setup["contract"].id), "file": f}, format="multipart").json()["id"]
    n1 = Clause.objects.filter(document_id=doc_id).count()
    r = client.post("/api/v1/clauses/extract/", {"document": doc_id}, format="json")
    assert r.status_code == 200
    assert r.json()["clauses"] == n1  # no duplicates
