"""Phase 24 tests — Vercel-native deployment paths.

Local backends (SQLite, filesystem storage, eager Celery) keep working; every
Vercel behavior is env-selected and covered here.
"""
import json
import os

from core.vercel import is_vercel, vercel_env


def test_vercel_env_detection(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    assert is_vercel() is False
    assert vercel_env() is None
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "production")
    assert is_vercel() is True
    assert vercel_env() == "production"


def test_vercel_mode_off_by_default():
    from django.conf import settings

    assert settings.VERCEL_DEPLOYMENT is False
    assert settings.DOCUMENT_STORAGE_BACKEND == "local"
    assert settings.CRON_SECRET == ""


def _load_settings_with(env: dict) -> dict:
    import subprocess
    import sys

    backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
    merged = {**os.environ, **env}
    code = (
        "import os, django;"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings');"
        "django.setup();"
        "from django.conf import settings;"
        "print(settings.VERCEL_DEPLOYMENT);"
        "print(settings.DOCUMENT_STORAGE_BACKEND);"
        "print(settings.CSRF_TRUSTED_ORIGINS);"
        "print(settings.FRONTEND_URL)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=backend_dir, capture_output=True, text=True, env=merged, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.splitlines()


def test_vercel_env_selection():
    lines = _load_settings_with({
        "VERCEL_DEPLOYMENT": "True",
        "DOCUMENT_STORAGE_BACKEND": "vercel_blob",
        "CRON_SECRET": "s3cret",
        "FRONTEND_URL": "https://app.example.com",
        "CORS_ALLOWED_ORIGINS": "https://app.example.com",
    })
    assert lines[0] == "True"
    assert lines[1] == "vercel_blob"
    assert "https://app.example.com" in lines[2]  # CSRF follows CORS origins


def test_no_silent_sqlite_in_production():
    import subprocess
    import sys

    backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    env.update({
        "DJANGO_DEBUG": "False",
        "DJANGO_SECRET_KEY": "long-enough-test-secret-key-0123456789abcdef",
        "DJANGO_ALLOWED_HOSTS": "example.com",
    })
    proc = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=backend_dir, capture_output=True, text=True, env=env, timeout=120,
    )
    assert proc.returncode != 0
    assert "DATABASE_URL" in proc.stderr


def test_vercel_entrypoint_exports_wsgi_app():
    """api/index.py must expose a Django WSGI app using existing config only."""
    import importlib.util
    import subprocess
    import sys

    root = os.path.join(os.path.dirname(__file__), "..")
    code = (
        "import importlib.util;"
        f"spec = importlib.util.spec_from_file_location('vercel_api', {root!r} + '/api/index.py');"
        "mod = importlib.util.module_from_spec(spec);"
        "spec.loader.exec_module(mod);"
        "print(callable(mod.app))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root, capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "True"


# ---------------------------------------------------------------------------
# Vercel Blob storage (fake in-process Blob HTTP server — no real credentials).
# ---------------------------------------------------------------------------

import json as _json
import threading as _threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


class _FakeBlobHandler(BaseHTTPRequestHandler):
    store: dict = {}
    seen: list = []

    def log_message(self, *args):  # quiet
        pass

    def _auth_ok(self):
        return self.headers.get("authorization") == "Bearer test-token"

    def do_PUT(self):
        length = int(self.headers.get("content-length", 0))
        data = self.rfile.read(length)
        query = parse_qs(urlparse(self.path).query)
        pathname = query.get("pathname", ["unnamed"])[0]
        type(self).seen.append({
            "method": "PUT", "pathname": pathname,
            "authorization": self.headers.get("authorization"),
            "access": self.headers.get("access"),
            "content_type": self.headers.get("x-content-type"),
        })
        if not self._auth_ok():
            self.send_response(401)
            self.end_headers()
            return
        url = f"http://127.0.0.1:{self.server.server_port}/blobs/{pathname}"
        type(self).store[url] = data
        body = _json.dumps({"url": url, "pathname": pathname}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" and "url=" in (parsed.query or ""):
            # metadata probe (?url=...): 200 when known, 404 when absent.
            target = parse_qs(parsed.query).get("url", [""])[0]
            known = target in type(self).store
            self.send_response(200 if known else 404)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", "2")
            self.end_headers()
            self.wfile.write(b"{}")
            return
        url = f"http://127.0.0.1:{self.server.server_port}{parsed.path}"
        type(self).seen.append({"method": "GET", "url": url,
                                "authorization": self.headers.get("authorization")})
        data = type(self).store.get(url)
        if data is None or not self._auth_ok():
            self.send_response(404 if data is None else 401)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("content-type", "application/octet-stream")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        length = int(self.headers.get("content-length", 0))
        payload = _json.loads(self.rfile.read(length) or b"{}")
        for url in payload.get("urls", []):
            type(self).store.pop(url, None)
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", "2")
        self.end_headers()
        self.wfile.write(b"{}")


import pytest as _pytest


@_pytest.fixture
def blob_server():
    _FakeBlobHandler.store = {}
    _FakeBlobHandler.seen = []
    server = HTTPServer(("127.0.0.1", 0), _FakeBlobHandler)
    thread = _threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


def _blob_settings(base_url):
    from django.test import override_settings

    return override_settings(
        DOCUMENT_STORAGE_BACKEND="vercel_blob",
        BLOB_READ_WRITE_TOKEN="test-token",
        BLOB_API_BASE_URL=base_url,
        STORAGES={
            "default": {"BACKEND": "documents.storages.BlobStorage"},
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
            },
        },
    )


def test_blob_client_private_crud(blob_server):
    from documents.blobstore import BlobError, VercelBlobClient

    client = VercelBlobClient(base_url=blob_server, token="test-token")
    result = client.put("docs/a.pdf", b"%PDF-1.4 data", content_type="application/pdf")
    assert result.url.startswith(blob_server)
    put = [r for r in _FakeBlobHandler.seen if r["method"] == "PUT"][0]
    assert put["access"] == "private"  # never public
    assert put["authorization"] == "Bearer test-token"
    assert client.exists(result.url) is True
    assert client.download(result.url) == b"%PDF-1.4 data"
    client.delete(result.url)
    assert client.exists(result.url) is False
    with _pytest.raises(BlobError):
        client.download(result.url)


def test_blob_client_requires_token():
    from documents.blobstore import BlobError, VercelBlobClient

    with _pytest.raises(BlobError):
        VercelBlobClient(base_url="http://127.0.0.1:9", token="")


def test_blob_storage_backend_roundtrip(blob_server):
    from documents.storages import BlobStorage

    with _blob_settings(blob_server):
        storage = BlobStorage()
        from django.core.files.base import ContentFile

        name = storage.save("docs/b.pdf", ContentFile(b"%PDF-1.4 x", name="b.pdf"))
        assert name.startswith(blob_server)  # opaque URL identifier, not a path
        assert storage.exists(name) is True
        with storage.open(name, "rb") as f:
            assert f.read() == b"%PDF-1.4 x"
        with _pytest.raises(ValueError):
            storage.url(name)  # private: no public URL, ever
        storage.delete(name)


def test_no_redis_required_in_vercel_mode(db):
    """With eager off but VERCEL_DEPLOYMENT on, uploads still process inline.

    Proves the Vercel path never touches the broker (no Redis is running in
    this test — a .delay() call would fail loudly instead of returning READY).
    """
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import override_settings
    from rest_framework.test import APIClient

    from contracts.models import Contract
    from organizations.models import Organization, OrganizationMembership
    from workspaces.models import Workspace, WorkspaceMembership

    User = get_user_model()
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False, VERCEL_DEPLOYMENT=True):
        user = User.objects.create_user(email="novredis@example.com", password="password123")
        org = Organization.objects.create(name="Acme", created_by=user)
        OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
        ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
        WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
        contract = Contract.objects.create(workspace=ws, title="MSA", created_by=user)

        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "The Vendor shall maintain insurance at all times during the term.")
        pdf = bytes(doc.tobytes())
        doc.close()

        client = APIClient()
        client.force_authenticate(user=user)
        f = SimpleUploadedFile("v.pdf", pdf, content_type="application/pdf")
        r = client.post("/api/v1/documents/", {"contract": str(contract.id), "file": f}, format="multipart")
        assert r.status_code == 201, r.content
        assert r.json()["status"] == "READY"


def test_blob_upload_processes_end_to_end(blob_server, db):
    """Full pipeline on Blob storage: upload → temp download → READY → download."""
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile
    from rest_framework.test import APIClient

    from contracts.models import Contract
    from documents.models import Document
    from obligations.models import Obligation
    from organizations.models import Organization, OrganizationMembership
    from workspaces.models import Workspace, WorkspaceMembership

    User = get_user_model()
    with _blob_settings(blob_server):
        user = User.objects.create_user(email="blob@example.com", password="password123")
        org = Organization.objects.create(name="Acme", created_by=user)
        OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
        ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
        WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
        contract = Contract.objects.create(workspace=ws, title="Blob MSA", created_by=user)

        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "The Vendor shall maintain insurance at all times during the term.")
        pdf = bytes(doc.tobytes())
        doc.close()

        client = APIClient()
        client.force_authenticate(user=user)
        f = SimpleUploadedFile("blob.pdf", pdf, content_type="application/pdf")
        r = client.post("/api/v1/documents/", {"contract": str(contract.id), "file": f}, format="multipart")
        assert r.status_code == 201, r.content
        assert r.json()["status"] == "READY"  # processed via temp download, no local file
        assert Obligation.objects.filter(contract=contract).exists()  # clauses+obligations ran

        doc_id = r.json()["id"]
        stored = Document.objects.get(pk=doc_id)
        assert stored.file.name.startswith(blob_server)

        dl = client.get(f"/api/v1/documents/{doc_id}/download/")
        assert dl.status_code == 200
        assert b"%PDF" in b"".join(dl.streaming_content)  # streamed from Blob, permission-checked

        assert client.delete(f"/api/v1/documents/{doc_id}/").status_code == 204
        assert _FakeBlobHandler.store == {}  # blob deleted alongside the row
# ---------------------------------------------------------------------------

def _cron_setup(db):
    from django.contrib.auth import get_user_model

    from contracts.models import Contract
    from obligations.models import Obligation
    from organizations.models import Organization, OrganizationMembership
    from workspaces.models import Workspace, WorkspaceMembership

    User = get_user_model()
    user = User.objects.create_user(email="cron@example.com", password="password123")
    org = Organization.objects.create(name="Acme", created_by=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
    contract = Contract.objects.create(
        workspace=ws, title="MSA", start_date="2026-01-15", created_by=user)
    Obligation.objects.create(
        workspace=ws, contract=contract, title="Monthly reports",
        obligation_type="REPORTING", frequency="MONTHLY",
        source_text="The Vendor shall deliver monthly reports.", status="ACTIVE")
    return ws


def test_cron_rejects_unauthenticated(db):
    from rest_framework.test import APIClient

    anon = APIClient()
    for url in ("/api/internal/cron/recurring-deadlines/", "/api/internal/cron/deadline-scan/"):
        assert anon.get(url).status_code == 403
        assert anon.post(url).status_code == 403
        assert anon.get(url, HTTP_AUTHORIZATION="Bearer wrong").status_code == 403


def test_cron_recurring_deadlines_idempotent(db):
    from django.test import override_settings
    from rest_framework.test import APIClient

    from audit.models import AuditEvent
    from deadlines.models import Deadline

    _cron_setup(db)
    with override_settings(CRON_SECRET="s3cret"):
        client = APIClient()
        auth = {"HTTP_AUTHORIZATION": "Bearer s3cret"}
        first = client.post("/api/internal/cron/recurring-deadlines/", **auth)
        assert first.status_code == 200, first.content
        assert first.json()["ok"] is True
        assert first.json()["deadlines"] >= 1
        assert "contracts" not in first.json() and "results" not in first.json()  # no data leak
        second = client.get("/api/internal/cron/recurring-deadlines/", **auth)  # GET also accepted (Vercel sends GET)
        assert second.status_code == 200
        assert second.json()["deadlines"] == 0  # idempotent: nothing new
        assert Deadline.objects.filter(kind="RECURRING").exists()
        assert AuditEvent.objects.filter(action="cron.recurring_generated").exists()


def test_cron_deadline_scan_idempotent(db):
    from datetime import date, timedelta

    from django.test import override_settings
    from rest_framework.test import APIClient

    from audit.models import AuditEvent
    from contracts.models import Contract
    from deadlines.models import Deadline
    from workspaces.models import Workspace

    ws = _cron_setup(db)
    contract = Contract.objects.filter(workspace=ws).first()
    Deadline.objects.create(
        workspace=ws, contract=contract, title="Renewal",
        kind="RENEWAL", due_date=date.today() + timedelta(days=3), rule="test")
    with override_settings(CRON_SECRET="s3cret"):
        client = APIClient()
        auth = {"HTTP_AUTHORIZATION": "Bearer s3cret"}
        first = client.post("/api/internal/cron/deadline-scan/", **auth)
        assert first.status_code == 200, first.content
        assert first.json()["notifications"] >= 1
        second = client.post("/api/internal/cron/deadline-scan/", **auth)
        assert second.json()["notifications"] == 0  # per-day dedupe: safe rerun
        assert AuditEvent.objects.filter(action="cron.deadline_scan").exists()


def test_cron_disabled_without_secret(db):
    """With no CRON_SECRET configured, every cron call is rejected."""
    from rest_framework.test import APIClient

    _cron_setup(db)
    anon = APIClient()
    assert anon.post("/api/internal/cron/recurring-deadlines/",
                     HTTP_AUTHORIZATION="Bearer anything").status_code == 403


# ---------------------------------------------------------------------------
# Access control, eval flow, Celery intactness, vercel.json structure.
# ---------------------------------------------------------------------------

def test_blob_download_rejects_unauthorized(blob_server, db):
    """Anonymous and cross-workspace users get 401/404 — never Blob bytes."""
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile
    from rest_framework.test import APIClient

    from contracts.models import Contract
    from organizations.models import Organization, OrganizationMembership
    from workspaces.models import Workspace, WorkspaceMembership

    User = get_user_model()
    with _blob_settings(blob_server):
        user = User.objects.create_user(email="priv@example.com", password="password123")
        stranger = User.objects.create_user(email="stranger@example.com", password="password123")
        org = Organization.objects.create(name="Acme", created_by=user)
        OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
        ws = Workspace.objects.create(organization=org, name="Legal", created_by=user)
        WorkspaceMembership.objects.create(workspace=ws, user=user, role="OWNER")
        contract = Contract.objects.create(workspace=ws, title="MSA", created_by=user)

        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "The Vendor shall maintain insurance at all times during the term.")
        pdf = bytes(doc.tobytes())
        doc.close()

        client = APIClient()
        client.force_authenticate(user=user)
        f = SimpleUploadedFile("p.pdf", pdf, content_type="application/pdf")
        doc_id = client.post(
            "/api/v1/documents/", {"contract": str(contract.id), "file": f}, format="multipart").json()["id"]

        anon = APIClient()
        assert anon.get(f"/api/v1/documents/{doc_id}/download/").status_code in (401, 403)
        other = APIClient()
        other.force_authenticate(user=stranger)
        assert other.get(f"/api/v1/documents/{doc_id}/download/").status_code == 404
        assert other.get(f"/api/v1/documents/{doc_id}/").status_code == 404


def test_public_eval_flow_in_vercel_mode(db):
    """Eval session works with VERCEL_DEPLOYMENT on (no login, no keys, no broker)."""
    from django.test import override_settings
    from rest_framework.test import APIClient

    from eval.seed import seed_eval_workspace

    seed_eval_workspace()
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False, VERCEL_DEPLOYMENT=True):
        anon = APIClient()
        r = anon.post("/api/v1/eval/session/")
        assert r.status_code == 200, r.content
        authed = APIClient(HTTP_AUTHORIZATION=f"Token {r.json()['token']}")
        contracts = authed.get("/api/v1/contracts/").json()
        assert contracts["count"] == 6


def test_celery_docker_path_intact():
    """Celery modules import; Beat schedule unchanged; tasks registered."""
    from config.celery import app as celery_app
    from django.conf import settings

    for dotted in ("documents.tasks", "clauses.tasks", "deadlines.tasks",
                   "notifications.tasks", "risks.tasks"):
        __import__(dotted)
    tasks = {v["task"] for v in settings.CELERY_BEAT_SCHEDULE.values()}
    assert tasks == {"deadlines.generate_recurring", "notifications.deadline_scan"}
    registered = set(celery_app.tasks.keys())
    assert "documents.process_document" in registered
    assert "deadlines.generate_recurring" in registered
    assert "notifications.deadline_scan" in registered
    assert "risks.assess_workspace" in registered


def test_vercel_json_structure():
    """vercel.json is valid and wires frontend, function, rewrites, crons."""
    root = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(root, "vercel.json")) as fh:
        config = json.load(fh)
    assert config["outputDirectory"] == "frontend/dist"
    assert "collectstatic" in config["buildCommand"]
    func = config["functions"]["api/index.py"]
    assert func["maxDuration"] == 300  # extended only for the API function
    assert os.path.exists(os.path.join(root, "api", "index.py"))
    sources = [r["source"] for r in config["rewrites"]]
    assert "/api/:path*" in sources
    assert any("index.html" in r["destination"] for r in config["rewrites"])  # SPA fallback
    cron_paths = [c["path"] for c in config["crons"]]
    assert "/api/internal/cron/recurring-deadlines/" in cron_paths
    assert "/api/internal/cron/deadline-scan/" in cron_paths

    # Every cron path must resolve in the Django URLconf.
    from django.urls import resolve

    for path in cron_paths:
        assert resolve(path).func is not None

    # Root dependency files the Vercel build needs must exist.
    assert os.path.exists(os.path.join(root, "requirements.txt"))
    assert os.path.exists(os.path.join(root, ".python-version"))
