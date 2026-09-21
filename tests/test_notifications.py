"""Phase 16 tests — notifications, prefs, dedupe, hooks, email abstraction."""
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from contracts.models import Contract
from deadlines.models import Deadline
from notifications.models import Notification, NotificationPreference
from notifications.services import notify_deadline_scan
from obligations.models import Obligation
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


@pytest.fixture
def setup(db):
    owner = User.objects.create_user(email="n1@example.com", password="password123")
    admin = User.objects.create_user(email="n2@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=owner)
    for u, role in ((owner, "OWNER"), (admin, "ADMIN")):
        OrganizationMembership.objects.create(organization=org, user=u, role=role)
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=owner)
    for u, role in ((owner, "OWNER"), (admin, "ADMIN")):
        WorkspaceMembership.objects.create(workspace=ws, user=u, role=role)
    contract = Contract.objects.create(workspace=ws, title="MSA", created_by=owner)
    return {"owner": owner, "admin": admin, "ws": ws, "contract": contract}


def test_assignment_notifies_assignee_with_email(setup):
    ob = Obligation.objects.create(
        workspace=setup["ws"], contract=setup["contract"], title="Duty",
        obligation_type="GENERAL", source_text="x", status="ACTIVE")
    client = APIClient()
    client.force_authenticate(user=setup["owner"])
    with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                           DEFAULT_FROM_EMAIL="test@local"):
        r = client.post(f"/api/v1/obligations/{ob.id}/assign/", {"email": "n2@example.com"}, format="json")
    assert r.status_code == 200
    notif = Notification.objects.get(user=setup["admin"], kind="obligation_assigned")
    assert notif.entity_id == str(ob.id) and notif.email_sent is True
    assert len(mail.outbox) == 1 and "Assigned" in mail.outbox[0].subject


def test_email_opt_out_skips_email(setup):
    NotificationPreference.objects.create(user=setup["admin"], kind="obligation_assigned", in_app=True, email=False)
    ob = Obligation.objects.create(
        workspace=setup["ws"], contract=setup["contract"], title="Duty",
        obligation_type="GENERAL", source_text="x", status="ACTIVE")
    client = APIClient()
    client.force_authenticate(user=setup["owner"])
    with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
        client.post(f"/api/v1/obligations/{ob.id}/assign/", {"email": "n2@example.com"}, format="json")
    notif = Notification.objects.get(user=setup["admin"], kind="obligation_assigned")
    assert notif.email_sent is False
    assert len(mail.outbox) == 0


def test_deadline_scan_dedupes_per_day(setup):
    Deadline.objects.create(
        workspace=setup["ws"], contract=setup["contract"], title="Renewal",
        kind="RENEWAL", due_date=date.today() + timedelta(days=3), rule="test")
    assert notify_deadline_scan(workspace=setup["ws"]) == 2  # owner + admin
    assert notify_deadline_scan(workspace=setup["ws"]) == 0  # dedupe: nothing new
    assert Notification.objects.filter(kind="deadline_approaching").count() == 2


def test_contract_processed_notifies_other_managers(setup):
    import fitz

    client = APIClient()
    client.force_authenticate(user=setup["owner"])
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "The Vendor shall maintain insurance at all times during the term.")
    data = bytes(doc.tobytes())
    doc.close()
    f = SimpleUploadedFile("np.pdf", data, content_type="application/pdf")
    assert client.post("/api/v1/documents/", {"contract": str(setup["contract"].id), "file": f}, format="multipart").status_code == 201
    assert Notification.objects.filter(user=setup["admin"], kind="contract_processed").exists()
    assert not Notification.objects.filter(user=setup["owner"], kind="contract_processed").exists()


def test_read_flow_and_isolation(setup):
    Notification.objects.create(workspace=setup["ws"], user=setup["owner"], kind="risk_increased", title="R")
    client = APIClient()
    client.force_authenticate(user=setup["owner"])
    assert client.get("/api/v1/notifications/unread-count/").json()["unread"] == 1
    nid = client.get("/api/v1/notifications/").json()["results"][0]["id"]
    assert client.post(f"/api/v1/notifications/{nid}/read/").json()["read"] is True
    assert client.get("/api/v1/notifications/unread-count/").json()["unread"] == 0

    outsider = User.objects.create_user(email="nx@example.com", password="password123")
    other = APIClient()
    other.force_authenticate(user=outsider)
    assert other.get("/api/v1/notifications/").json()["count"] == 0
    assert other.get("/api/v1/notifications/unread-count/").json()["unread"] == 0
