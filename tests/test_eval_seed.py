"""Eval seed production-readiness: idempotent builds, honest endpoints, safe pipeline."""
from django.core.management import call_command
from rest_framework.test import APIClient

from contracts.models import Contract
from documents.models import Document
from eval.seed import EVAL_ORG_SLUG, EVAL_PUBLIC_SLUG, seed_eval_workspace
from obligations.models import Obligation
from organizations.models import Organization
from workspaces.models import Workspace


def _seed_counts():
    ws = Workspace.objects.get(workspace_type="PUBLIC_EVAL", public_slug=EVAL_PUBLIC_SLUG)
    return {
        "workspace": str(ws.id),
        "contracts": Contract.objects.filter(workspace=ws).count(),
        "documents": Document.objects.filter(workspace=ws).count(),
        "obligations": Obligation.objects.filter(workspace=ws).count(),
        "users": Organization.objects.get(slug=EVAL_ORG_SLUG).memberships.count(),
    }


def test_seed_twice_no_duplicates(db):
    first = seed_eval_workspace()
    assert first["skipped"] is False
    assert first["contracts"] == 6
    assert first["obligations"] >= 40
    before = _seed_counts()

    second = seed_eval_workspace()
    assert second["skipped"] is True
    after = _seed_counts()

    assert before == after  # same workspace, same rows, nothing rebuilt
    assert Organization.objects.filter(slug=EVAL_ORG_SLUG).count() == 1
    assert Workspace.objects.filter(workspace_type="PUBLIC_EVAL", public_slug=EVAL_PUBLIC_SLUG).count() == 1


def test_seed_preserves_recruiter_state(db):
    seed_eval_workspace()
    ws = Workspace.objects.get(workspace_type="PUBLIC_EVAL", public_slug=EVAL_PUBLIC_SLUG)
    extra = Contract.objects.create(workspace=ws, title="Recruiter Upload")
    Document.objects.create(
        workspace=ws, contract=extra, original_filename="mine.pdf",
        mime="application/pdf", size_bytes=10, sha256="recruiter-bytes",
        status="UPLOADED")

    rerun = seed_eval_workspace()

    assert rerun["skipped"] is True  # no wipe: recruiter data survives redeploys
    assert Contract.objects.filter(pk=extra.pk).exists()
    assert Document.objects.filter(sha256="recruiter-bytes").exists()
    assert Contract.objects.filter(workspace=ws).count() == 7  # 6 seeded + 1 recruiter


def test_eval_info_seeded_true(db):
    seed_eval_workspace()
    r = APIClient().get("/api/v1/eval/info/")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["seeded"] is True
    assert body["contracts"] == 6
    assert body["obligations"] >= 40


def test_eval_info_unseeded_false(db):
    r = APIClient().get("/api/v1/eval/info/")
    assert r.status_code == 200
    assert r.json() == {"enabled": True, "seeded": False}


def test_build_script_production_seed_contract():
    """The committed build pipeline must gate seeding correctly and loudly."""
    with open("scripts/vercel-build.sh", encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    text = "\n".join(lines)
    assert "set -euo pipefail" in text  # any failure fails the build
    assert "VERCEL_ENV" in text and '"production"' in text.replace("'", '"')
    assert "manage.py migrate --noinput" in text
    seed_lines = [ln for ln in lines if "manage.py seed_eval" in ln]
    assert len(seed_lines) == 1
    assert "||" not in seed_lines[0], "seed failure must fail the build, never be swallowed"
    for ln in lines:
        if ln.strip().startswith("echo"):
            for secret in ("DATABASE_URL", "SECRET_KEY", "BLOB_READ_WRITE_TOKEN",
                           "CRON_SECRET", "PASSWORD", "POSTGRES_PASSWORD"):
                assert f"${secret}" not in ln and f"${{{secret}" not in ln, \
                    f"secret value expanded in build echo: {ln}"


def test_seed_command_reports_skip_state(db, capsys):
    call_command("seed_eval")
    first_out = capsys.readouterr().out
    assert "Evaluation workspace seeded" in first_out
    call_command("seed_eval")
    second_out = capsys.readouterr().out
    assert "skipped" in second_out  # second run is a no-op, and says so
