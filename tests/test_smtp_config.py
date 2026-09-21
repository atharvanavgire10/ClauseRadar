"""FIX 2 tests — SMTP settings load from environment (fresh interpreter)."""
import os
import subprocess
import sys

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")

LOADER = (
    "import os, django;"
    "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings');"
    "django.setup();"
    "from django.conf import settings;"
    "print(settings.EMAIL_BACKEND);"
    "print(settings.EMAIL_HOST);"
    "print(settings.EMAIL_PORT);"
    "print(repr(settings.EMAIL_HOST_USER));"
    "print(repr(settings.EMAIL_HOST_PASSWORD));"
    "print(settings.EMAIL_USE_TLS);"
    "print(settings.EMAIL_USE_SSL);"
    "print(settings.DEFAULT_FROM_EMAIL)"
)


def load_with(env: dict) -> list[str]:
    merged = {**os.environ, **env}
    proc = subprocess.run(
        [sys.executable, "-c", LOADER],
        cwd=BACKEND_DIR, capture_output=True, text=True, env=merged, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.splitlines()


def test_console_defaults_without_smtp_env():
    lines = load_with({"EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend"})
    assert lines[0] == "django.core.mail.backends.console.EmailBackend"
    assert lines[1] == "localhost"
    assert lines[2] == "587"
    assert lines[5] == "True" and lines[6] == "False"


def test_smtp_env_mapping():
    lines = load_with({
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "EMAIL_HOST": "smtp.example.com",
        "EMAIL_PORT": "2525",
        "EMAIL_HOST_USER": "mailer",
        "EMAIL_HOST_PASSWORD": "s3cret",
        "EMAIL_USE_TLS": "False",
        "EMAIL_USE_SSL": "True",
        "DEFAULT_FROM_EMAIL": "Ops <ops@example.com>",
    })
    assert lines[0] == "django.core.mail.backends.smtp.EmailBackend"
    assert lines[1] == "smtp.example.com"
    assert lines[2] == "2525"
    assert lines[3] == "'mailer'" and lines[4] == "'s3cret'"
    assert lines[5] == "False" and lines[6] == "True"
    assert lines[7] == "Ops <ops@example.com>"


def test_locmem_send_path():
    """The notification email helper delivers through the configured backend."""
    from django.core import mail
    from django.test import override_settings

    from notifications.email import send_notification_email

    with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
        assert send_notification_email("a@example.com", "Subject", "Body") is True
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["a@example.com"]
