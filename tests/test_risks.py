"""Phase 09 tests — explainable risk scoring (no random scores)."""
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from contracts.models import Contract
from deadlines.models import Deadline
from obligations.models import Obligation
from organizations.models import Organization, OrganizationMembership
from risks.models import RiskFinding
from risks.rules import assess_contract, level_for
from risks.services import assess_contract_risks
from workspaces.models import Workspace, WorkspaceMembership

User = get_user_model()


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email="rk@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    contract = Contract.objects.create(workspace=ws, title="Risky MSA", created_by=user)
    return {"user": user, "ws": ws, "contract": contract}


def _ob(setup, **kw):
    params = {"workspace": setup["ws"], "contract": setup["contract"], "title": "Duty",
              "obligation_type": "GENERAL", "frequency": "ONE_TIME",
              "source_text": "The Vendor shall do the thing described here.", "status": "ACTIVE"}
    params.update(kw)
    return Obligation.objects.create(**params)


def test_spec_example_composition(setup):
    """Overdue 30 + missing evidence 20 + liability 25 + no owner 7 = 82."""
    from clauses.models import Clause
    from documents.models import Document

    doc = Document.objects.create(
        workspace=setup["ws"], contract=setup["contract"], file="test/manual.pdf",
        original_filename="manual.pdf", mime="application/pdf", size_bytes=10,
        sha256="abc123", status="READY",
    )
    clause = Clause.objects.create(
        workspace=setup["ws"], contract=setup["contract"], document=doc,
        page_number=1, text="Limitation of liability shall be capped at fees paid.",
        clause_type="LIABILITY", confidence=0.8,
    )
    ob = _ob(setup, clause=clause, obligation_type="GENERAL",
             evidence_required="insurance certificate", owner=None)
    Deadline.objects.create(
        workspace=setup["ws"], contract=setup["contract"], obligation=ob,
        title="Notice", kind="FIXED", due_date=date.today() - timedelta(days=3),
        rule="test overdue",
    )
    score, findings = assess_contract(setup["contract"])
    assert score == 82
    by_rule = {f["rule"]: f for f in findings}
    assert by_rule["deadline_overdue"]["points"] == 30
    assert by_rule["evidence_missing"]["points"] == 20
    assert by_rule["liability_exposure"]["points"] == 25
    assert by_rule["no_owner"]["points"] == 7
    # Every finding explains itself and cites its source + affected obligation.
    for f in findings:
        assert f["explanation"] and f["obligation"] is not None and f["evidence"]


def test_levels():
    assert level_for(0) == "LOW" and level_for(30) == "MEDIUM"
    assert level_for(60) == "HIGH" and level_for(82) == "CRITICAL" and level_for(100) == "CRITICAL"


def test_clean_contract_scores_zero(setup):
    _ob(setup, status="COMPLETED", owner=setup["user"])
    score, findings = assess_contract(setup["contract"])
    assert score == 0 and findings == []


def test_assess_service_persists_and_regenerates(setup):
    ob = _ob(setup)
    first = assess_contract_risks(setup["contract"].id)
    assert first["score"] >= 7  # no_owner at minimum
    assert RiskFinding.objects.filter(contract=setup["contract"]).count() == len(first["findings"])
    second = assess_contract_risks(setup["contract"].id)
    assert second["score"] == first["score"]
    assert RiskFinding.objects.filter(contract=setup["contract"]).count() == len(first["findings"])  # no dupes


def test_risk_api_summary_assess_isolation(setup):
    _ob(setup)
    assess_contract_risks(setup["contract"].id)
    client = APIClient()
    client.force_authenticate(user=setup["user"])
    r = client.get(f"/api/v1/risks/summary/?contract={setup['contract'].id}")
    assert r.status_code == 200
    body = r.json()
    assert body["score"] >= 0 and body["level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert body["findings"] and body["findings"][0]["points"] > 0

    outsider = User.objects.create_user(email="ro@example.com", password="password123")
    other = APIClient()
    other.force_authenticate(user=outsider)
    assert other.get(f"/api/v1/risks/summary/?contract={setup['contract'].id}").status_code in (403, 404)
    assert other.get("/api/v1/risks/").json()["count"] == 0
