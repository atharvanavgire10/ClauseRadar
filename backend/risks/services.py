"""Risk assessment services — regenerate findings per contract (idempotent)."""
from __future__ import annotations

from django.db import transaction

from audit.services import log_event
from .models import RiskFinding
from .rules import assess_contract, level_for


def assess_contract_risks(contract_id) -> dict:
    """Delete + rebuild findings for a contract. Returns {score, level, findings}."""
    from contracts.models import Contract

    with transaction.atomic():
        contract = Contract.objects.select_related("workspace").get(pk=contract_id)
        previous_rows = list(RiskFinding.objects.filter(contract=contract))
        previous = min(100, sum(f.points for f in previous_rows)) if previous_rows else None
        RiskFinding.objects.filter(contract=contract).delete()
        score, finding_dicts = assess_contract(contract)
        rows = [
            RiskFinding(
                workspace=contract.workspace, contract=contract,
                obligation=f["obligation"], rule=f["rule"], points=f["points"],
                severity=f["severity"], title=f["title"][:300],
                explanation=f["explanation"], evidence=f["evidence"],
            )
            for f in finding_dicts
        ]
        RiskFinding.objects.bulk_create(rows)
        findings = list(RiskFinding.objects.filter(contract=contract).order_by("-points"))
        log_event(actor=None, organization=contract.workspace.organization, workspace=contract.workspace,
                  entity_type="contract", entity_id=contract.id, action="contract.risk_assessed",
                  metadata={"score": score, "level": level_for(score), "findings": len(findings)})
        try:
            from notifications.services import notify_risk_increased

            notify_risk_increased(workspace=contract.workspace, contract=contract,
                                  score=score, previous=previous)
        except Exception:  # pragma: no cover
            pass
        return {"score": score, "level": level_for(score),
                "findings": findings, "contract": contract}


def assess_workspace_risks(workspace_id) -> list[dict]:
    from contracts.models import Contract

    return [assess_contract_risks(c.id)
            for c in Contract.objects.filter(workspace_id=workspace_id)]
