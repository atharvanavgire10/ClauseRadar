"""Phase 08 tests — recurrence math, idempotent generation, no duplicates."""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from freezegun import freeze_time
from rest_framework.test import APIClient

from contracts.models import Contract
from deadlines.engine import add_months, occurrence_dates
from deadlines.models import Deadline
from deadlines.services import generate_recurring_for_obligation
from obligations.models import Obligation
from organizations.models import Organization, OrganizationMembership
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


def test_add_months_clamps_month_end():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)  # leap year
    assert add_months(date(2026, 10, 15), 3) == date(2027, 1, 15)
    assert add_months(date(2026, 5, 15), -1) == date(2026, 4, 15)


def test_monthly_series_deterministic():
    with freeze_time("2026-09-21"):
        from deadlines.engine import today_in_tz

        dates = occurrence_dates("MONTHLY", date(2026, 1, 15), today=today_in_tz(), count=3)
    assert dates == [date(2026, 10, 15), date(2026, 11, 15), date(2026, 12, 15)]


def test_quarterly_and_annual():
    assert occurrence_dates("QUARTERLY", date(2026, 1, 10), today=date(2026, 9, 21), count=2) == [
        date(2026, 10, 10), date(2027, 1, 10)]
    assert occurrence_dates("ANNUAL", date(2025, 3, 1), today=date(2026, 9, 21), count=2) == [
        date(2027, 3, 1), date(2028, 3, 1)]


def test_weekly_steps():
    assert occurrence_dates("WEEKLY", date(2026, 9, 14), today=date(2026, 9, 21), count=2) == [
        date(2026, 9, 28), date(2026, 10, 5)]


def test_non_recurring_raises():
    with pytest.raises(ValueError):
        occurrence_dates("ONE_TIME", date(2026, 1, 1), today=date(2026, 9, 21))
    with pytest.raises(ValueError):
        occurrence_dates("CUSTOM", date(2026, 1, 1), today=date(2026, 9, 21))


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email="rc@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    contract = Contract.objects.create(workspace=ws, title="MSA", start_date=date(2026, 1, 15), created_by=user)
    return {"user": user, "ws": ws, "contract": contract}


def _ob(setup, **kw):
    params = {"workspace": setup["ws"], "contract": setup["contract"], "title": "Monthly reports",
              "obligation_type": "REPORTING", "frequency": "MONTHLY",
              "source_text": "Monthly reports.", "status": "ACTIVE"}
    params.update(kw)
    return Obligation.objects.create(**params)


def test_generation_idempotent_no_duplicates(setup):
    ob = _ob(setup)
    with freeze_time("2026-09-21"):
        assert generate_recurring_for_obligation(ob.id, occurrences=3) == 3
        assert generate_recurring_for_obligation(ob.id, occurrences=3) == 0  # retry: nothing new
    assert Deadline.objects.filter(obligation=ob, kind="RECURRING").count() == 3
    dates = list(Deadline.objects.filter(obligation=ob).order_by("due_date").values_list("due_date", flat=True))
    assert dates == [date(2026, 10, 15), date(2026, 11, 15), date(2026, 12, 15)]


def test_one_time_yields_nothing(setup):
    ob = _ob(setup, frequency="ONE_TIME")
    assert generate_recurring_for_obligation(ob.id) == 0


def test_terminal_states_skipped(setup):
    ob = _ob(setup, status="REJECTED")
    assert generate_recurring_for_obligation(ob.id) == 0


def test_activation_auto_generates_recurring(setup):
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    ob = _ob(setup, frequency="QUARTERLY", status="CONFIRMED")
    # NOTE: no freeze_time around API calls — freezegun breaks DRF throttling.
    r = client.post(f"/api/v1/obligations/{ob.id}/activate/")
    assert r.status_code == 200
    assert r.json()["status"] == "ACTIVE"
    assert Deadline.objects.filter(obligation=ob, kind="RECURRING").count() == 6


def test_generate_recurring_endpoint_and_isolation(setup):
    outsider = User.objects.create_user(email="oo@example.com", password="password123")
    ob = _ob(setup)
    client = APIClient()
    client.force_authenticate(user=outsider)
    r = client.post("/api/v1/deadlines/generate-recurring/", {"obligation": str(ob.id)}, format="json")
    assert r.status_code in (403, 404)
