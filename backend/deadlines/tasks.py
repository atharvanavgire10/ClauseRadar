from celery import shared_task

from .services import generate_for_workspace_contracts, generate_recurring_for_workspace


@shared_task(name="deadlines.generate_workspace")
def generate_workspace_deadlines(workspace_id: str) -> int:
    return generate_for_workspace_contracts(workspace_id)


@shared_task(name="deadlines.generate_recurring")
def generate_recurring_task(workspace_id: str | None = None) -> int:
    """Beat-scheduled roll-forward of recurring deadlines (idempotent)."""
    if workspace_id:
        return generate_recurring_for_workspace(workspace_id)
    from workspaces.models import Workspace

    return sum(generate_recurring_for_workspace(str(w.id)) for w in Workspace.objects.all())
