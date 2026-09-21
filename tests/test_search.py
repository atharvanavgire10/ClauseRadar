"""Phase 12 tests — unified search across all entity types."""
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
    user = User.objects.create_user(email="s@example.com", password="password123")
    outsider = User.objects.create_user(email="sx@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    contract = Contract.objects.create(
        workspace=ws, title="Cyber Insurance Master Agreement",
        description="Covers cyber insurance and breach notification duties.", created_by=user)
    return {"user": user, "outsider": outsider, "ws": ws, "contract": contract}


def upload(client, contract_id):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "The Vendor shall maintain valid cyber insurance throughout the term.")
    data = bytes(doc.tobytes())
    doc.close()
    f = SimpleUploadedFile("ins.pdf", data, content_type="application/pdf")
    return client.post("/api/v1/documents/", {"contract": str(contract_id), "file": f}, format="multipart")


def test_insurance_finds_contracts_clauses_obligations(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    assert upload(client, setup["contract"].id).status_code == 201
    r = client.get("/api/v1/search/?q=insurance")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 3
    assert set(body["counts"]) >= {"contract", "clause", "obligation"}
    for hit in body["results"]:
        assert {"type", "id", "title", "snippet", "rank"} <= set(hit)


def test_type_date_and_risk_filters(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    upload(client, setup["contract"].id)
    r = client.get("/api/v1/search/?q=insurance&types=contract")
    assert set(r.json()["counts"]) == {"contract"}
    r = client.get("/api/v1/search/?q=insurance&date_from=2000-01-01&date_to=2030-01-01")
    assert r.json()["count"] >= 3
    r = client.get("/api/v1/search/?q=insurance&date_from=2030-01-01")
    assert r.json()["count"] == 0
    # Empty query rejected.
    assert client.get("/api/v1/search/?q=x").status_code == 400
    assert client.get("/api/v1/search/").status_code == 400


def test_search_isolation(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    upload(client, setup["contract"].id)
    other = APIClient()
    other.force_authenticate(user=setup["outsider"])
    assert other.get("/api/v1/search/?q=insurance").json()["count"] == 0
