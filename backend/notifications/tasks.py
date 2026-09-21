from celery import shared_task


@shared_task(name="notifications.deadline_scan")
def deadline_scan_task(workspace_id: str | None = None) -> int:
    from .services import notify_deadline_scan
    from workspaces.models import Workspace

    if workspace_id:
        return notify_deadline_scan(workspace=Workspace.objects.get(pk=workspace_id))
    return sum(
        notify_deadline_scan(workspace=w) for w in Workspace.objects.all()
    )


@shared_task(name="notifications.send_email")
def send_email_task(notification_id: str) -> bool:
    """Reserved for worker-based email retries; eager mode sends inline."""
    from .email import send_notification_email
    from .models import Notification

    try:
        notif = Notification.objects.select_related("user").get(pk=notification_id)
    except Notification.DoesNotExist:
        return False
    return send_notification_email(notif.user.email, notif.title, notif.body or notif.title)
