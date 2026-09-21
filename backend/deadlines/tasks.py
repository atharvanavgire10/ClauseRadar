from celery import shared_task

from .services import generate_for_workspace_contracts


@shared_task(name="deadlines.generate_workspace")
def generate_workspace_deadlines(workspace_id: str) -> int:
    return generate_for_workspace_contracts(workspace_id)
