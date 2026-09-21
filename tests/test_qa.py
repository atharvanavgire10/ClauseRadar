"""Phase 15 tests — grounded answers, citations, insufficient-evidence honesty."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from contracts.models import Contract
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email="qa@example.com", password="password123")
    outsider = User.objects.create_user(email="qx@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    contract = Contract.objects.create(workspace=ws, title="Vendor MSA", created_by=user)
    return {"user": user, "outsider": outsider, "ws": ws, "contract": contract}


def upload(client, contract_id):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "The Vendor shall maintain valid cyber insurance throughout the term.")
    data = bytes(doc.tobytes())
    doc.close()
    f = SimpleUploadedFile("q.pdf", data, content_type="application/pdf")
    return client.post("/api/v1/documents/", {"contract": str(contract_id), "file": f}, format="multipart")


def ask(client, **payload):
    return client.post("/api/v1/ai/ask/", payload, format="json")


def test_insurance_question_cites_sources(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    assert upload(client, setup["contract"].id).status_code == 201
    r = ask(client, workspace=str(setup["ws"].id), question="What insurance obligations exist?")
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "insurance"
    assert "insurance" in body["answer"].lower()
    assert body["citations"], "answer must carry citations"
    cite = body["citations"][0]
    assert cite["document_id"] and cite["page_number"] and cite["clause_id"] and cite["source_text"]
    assert "insurance" in cite["source_text"].lower()


def test_insufficient_evidence_when_no_match(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    r = ask(client, workspace=str(setup["ws"].id), question="What insurance obligations exist?")
    assert r.status_code == 200
    assert r.json()["answer"] == "Insufficient evidence in the available documents."
    assert r.json()["citations"] == []


def test_overdue_and_general_intents(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    upload(client, setup["contract"].id)
    r = ask(client, workspace=str(setup["ws"].id), question="Which obligations are overdue?")
    assert r.status_code == 200
    assert r.json()["intent"] == "overdue"
    r = ask(client, contract=str(setup["contract"].id), question="Summarize obligations.")
    assert r.status_code == 200
    assert "obligation" in r.json()["answer"].lower()


def test_qa_isolation_and_validation(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    upload(client, setup["contract"].id)
    other = APIClient()
    other.force_authenticate(user=setup["outsider"])
    r = ask(other, workspace=str(setup["ws"].id), question="What insurance obligations exist?")
    assert r.status_code == 403
    assert ask(client, question="hi").status_code == 400
    assert ask(client, workspace=str(setup["ws"].id), question="x").status_code == 400
