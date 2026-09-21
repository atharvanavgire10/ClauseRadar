"""Phase 17 tests — public evaluation: no-signup access, isolation, reset."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from contracts.models import Contract
from eval.seed import seed_eval_workspace
from obligations.models import Obligation
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


@pytest.fixture
def eval_data(db):
    return seed_eval_workspace()


def eval_client():
    client = APIClient()  # no auth — public
    r = client.post("/api/v1/eval/session/")
    assert r.status_code == 200, r.content
    token = r.json()["token"]
    authed = APIClient(HTTP_AUTHORIZATION=f"Token {token}")
    return authed, r.json()["workspace"]


def test_session_without_signup_and_seed_shape(eval_data):
    assert eval_data["contracts"] == 6
    assert eval_data["obligations"] >= 40
    assert eval_data["versions"] == 8
    assert eval_data["deadlines"] >= 6
    assert eval_data["risks"] >= 1
    assert eval_data["audit"] >= 1


def test_visitor_uses_same_apis(eval_data):
    client, ws_id = eval_client()
    contracts = client.get("/api/v1/contracts/").json()
    assert contracts["count"] == 6
    cid = contracts["results"][0]["id"]
    assert client.get(f"/api/v1/contracts/{cid}/").status_code == 200
    assert client.get(f"/api/v1/contracts/{cid}/versions/").status_code == 200
    assert client.get(f"/api/v1/clauses/?contract={cid}").json()["count"] >= 1
    obs = client.get(f"/api/v1/obligations/?contract={cid}").json()
    assert obs["count"] >= 1
    assert client.get("/api/v1/search/?q=insurance").json()["count"] >= 1
    assert client.post("/api/v1/ai/ask/", {"workspace": ws_id, "question": "What insurance obligations exist?"}, format="json").status_code == 200


def test_visitor_mutations_permitted_fields(eval_data):
    client, _ = eval_client()
    ob = client.get("/api/v1/obligations/?status=NEEDS_REVIEW").json()["results"][0]
    oid = ob["id"]
    assert client.post(f"/api/v1/obligations/{oid}/confirm/").status_code == 200
    assert client.post(f"/api/v1/obligations/{oid}/activate/").status_code == 200
    assert client.patch(f"/api/v1/obligations/{oid}/", {"priority": "HIGH"}, format="json").status_code == 200


def test_visitor_isolated_from_private_data(eval_data, db):
    owner = User.objects.create_user(email="priv@example.com", password="password123")
    org = Organization.objects.create(name="Private", created_by=owner)
    OrganizationMembership.objects.create(organization=org, user=owner, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Secret", created_by=owner)
    WorkspaceMembership.objects.create(workspace=ws, user=owner, role="OWNER")
    secret = Contract.objects.create(workspace=ws, title="Secret Deal", created_by=owner)

    client, _ = eval_client()
    titles = [c["title"] for c in client.get("/api/v1/contracts/").json()["results"]]
    assert "Secret Deal" not in titles
    assert client.get(f"/api/v1/contracts/{secret.id}/").status_code == 404
    assert client.get("/api/v1/search/?q=Secret").json()["count"] == 0


def test_visitor_upload_and_review_own_pdf(eval_data):
    import fitz

    client, _ = eval_client()
    cid = client.get("/api/v1/contracts/").json()["results"][0]["id"]
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "The Vendor shall maintain insurance at all times during the term.")
    data = bytes(doc.tobytes())
    doc.close()
    f = SimpleUploadedFile("mine.pdf", data, content_type="application/pdf")
    r = client.post("/api/v1/documents/", {"contract": cid, "file": f}, format="multipart")
    assert r.status_code == 201, r.content
    assert r.json()["status"] == "READY"
    obs = client.get(f"/api/v1/obligations/?contract={cid}").json()
    assert obs["count"] >= 1


def test_reset_restores_seed(eval_data):
    anon = APIClient()
    client, _ = eval_client()
    cid = client.get("/api/v1/contracts/").json()["results"][0]["id"]
    client.post("/api/v1/contracts/", {"workspace": "x", "title": "junk"}, format="json")  # rejected, no-op
    before = Obligation.objects.filter(clause__isnull=False).count()
    assert before > 0
    r = anon.post("/api/v1/eval/reset/")
    assert r.status_code == 200
    assert r.json()["contracts"] == 6
    assert r.json()["obligations"] >= 40


def test_eval_session_rate_limited(db):
    # Real configured rate is 30/hour; exhaust it from one IP. This test must
    # stay last in this file: the throttle cache is per-process.
    anon = APIClient()
    codes = [anon.post("/api/v1/eval/session/").status_code for _ in range(31)]
    assert codes[0] == 200
    assert codes[-1] == 429, "session issuance must be rate limited"
