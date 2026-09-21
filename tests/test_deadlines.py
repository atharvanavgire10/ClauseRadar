"""Phase 07 tests — deadline engine math, statuses, generation, transitions."""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from freezegun import freeze_time
from rest_framework.test import APIClient

from contracts.models import Contract
from deadlines.engine import (
    add_business_days,
    deadline_status,
    ensure_aware,
    parse_explicit_date,
    parse_relative,
    renewal_notice_date,
    shift,
)
from deadlines.models import Deadline
from deadlines.services import generate_for_contract
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


def test_renewal_example_from_spec():
    # Renewal 15 Dec 2026, 60 days before → 16 Oct 2026.
    assert renewal_notice_date(date(2026, 12, 15), 60) == date(2026, 10, 16)


def test_business_days_skip_weekends():
    # Friday 2026-09-18 + 1 business day → Monday 2026-09-21.
    assert add_business_days(date(2026, 9, 18), 1) == date(2026, 9, 21)
    assert add_business_days(date(2026, 9, 21), -1) == date(2026, 9, 18)
    assert add_business_days(date(2026, 9, 21), 0) == date(2026, 9, 21)


def test_shift_before_after_and_business():
    assert shift(date(2026, 12, 15), 60, direction="before") == date(2026, 10, 16)
    assert shift(date(2026, 10, 16), 60, direction="after") == date(2026, 12, 15)
    assert shift(date(2026, 9, 18), 1, direction="after", business=True) == date(2026, 9, 21)
    with pytest.raises(ValueError):
        shift(date(2026, 1, 1), 5, direction="sideways")


def test_leap_year_boundary():
    assert shift(date(2024, 2, 28), 1, direction="after") == date(2024, 2, 29)
    assert shift(date(2023, 2, 28), 1, direction="after") == date(2023, 3, 1)


def test_parse_explicit_dates():
    assert parse_explicit_date("due on 2026-12-15 without fail") == date(2026, 12, 15)
    assert parse_explicit_date("effective 15 Dec 2026") == date(2026, 12, 15)
    assert parse_explicit_date("sometime next quarter") is None
    assert parse_explicit_date("no date here") is None


def test_parse_relative():
    assert parse_relative("pay within 30 days of invoice")["days"] == 30
    assert parse_relative("60 days before renewal") == {"days": 60, "unit": "day", "direction": "before", "hours": 0}
    assert parse_relative("no relative language") is None


def test_status_matrix():
    today = date(2026, 9, 21)
    assert deadline_status(date(2026, 9, 20), today) == "OVERDUE"
    assert deadline_status(date(2026, 9, 21), today) == "DUE_SOON"
    assert deadline_status(date(2026, 9, 28), today) == "DUE_SOON"
    assert deadline_status(date(2026, 10, 5), today) == "UPCOMING"
    assert deadline_status(date(2026, 9, 20), today, completed=True) == "COMPLETED"
    assert deadline_status(date(2026, 9, 20), today, waived=True) == "WAIVED"


def test_ensure_aware_naive_and_aware():
    from datetime import datetime, timezone

    naive = datetime(2026, 1, 1, 12, 0, 0)
    assert ensure_aware(naive).tzinfo is not None
    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert ensure_aware(aware) is aware


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email="dl@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    return {"user": user, "ws": ws}


def test_generation_never_invents_dates(setup):
    contract = Contract.objects.create(workspace=setup["ws"], title="Undated")
    assert generate_for_contract(contract.id) == 0
    assert Deadline.objects.filter(contract=contract).count() == 0


def test_generation_from_renewal_and_end(setup):
    contract = Contract.objects.create(
        workspace=setup["ws"], title="Dated",
        renewal_date=date(2026, 12, 15), end_date=date(2027, 12, 14),
    )
    assert generate_for_contract(contract.id) == 3
    kinds = {d.kind for d in Deadline.objects.filter(contract=contract)}
    assert kinds == {"RENEWAL", "RENEWAL_NOTICE", "EXPIRY"}
    notice = Deadline.objects.get(contract=contract, kind="RENEWAL_NOTICE")
    assert notice.due_date == date(2026, 11, 15)  # default 30 days before
    assert "30 days before" in notice.rule
    # Idempotent: second run creates nothing new.
    assert generate_for_contract(contract.id) == 0
    assert Deadline.objects.filter(contract=contract).count() == 3


def test_deadline_api_statuses_and_transitions(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    contract = Contract.objects.create(
        workspace=setup["ws"], title="D", renewal_date=date(2026, 12, 15),
    )
    client.post("/api/v1/deadlines/generate/", {"contract": str(contract.id)}, format="json")
    with freeze_time("2026-12-10"):
        r = client.get(f"/api/v1/deadlines/?contract={contract.id}&status=DUE_SOON")
        assert r.status_code == 200
        assert r.json()["count"] >= 1  # renewal 5 days out
    dl = Deadline.objects.filter(contract=contract, kind="RENEWAL").first()
    assert client.post(f"/api/v1/deadlines/{dl.id}/complete/").json()["status"] == "COMPLETED"
    assert client.post(f"/api/v1/deadlines/{dl.id}/reopen/").json()["status"] != "COMPLETED"
    assert client.post(f"/api/v1/deadlines/{dl.id}/waive/").json()["status"] == "WAIVED"
