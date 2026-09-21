"""Celery application bootstrap (Phase 00 skeleton; tasks arrive in later phases)."""
from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("clauseradar")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Smoke task that proves broker→worker→backend round-trips.

    Returns the executor identity so tests can distinguish real worker
    execution from eager in-process fallback (different PID).
    """
    import os as _os
    import socket as _socket

    print(f"Request: {self.request!r}")
    return {"hostname": _socket.gethostname(), "pid": _os.getpid()}
