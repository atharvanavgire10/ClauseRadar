"""Email abstraction — Django email backend (console by default), never fatal."""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_notification_email(to_email: str, subject: str, body: str) -> bool:
    """Send one notification email. Returns True on success, False otherwise."""
    if not to_email:
        return False
    try:
        send_mail(
            subject=f"[ClauseRadar] {subject}",
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@clauseradar.local"),
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception as exc:  # pragma: no cover - backend misconfiguration guard
        logger.warning("notification email failed: %s", exc)
        return False
