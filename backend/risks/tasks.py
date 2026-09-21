from celery import shared_task

from .services import assess_workspace_risks


@shared_task(name="risks.assess_workspace")
def assess_workspace_task(workspace_id: str) -> int:
    results = assess_workspace_risks(workspace_id)
    return sum(1 for _ in results)
