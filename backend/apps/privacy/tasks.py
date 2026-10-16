from __future__ import annotations

from celery import shared_task

from .services import process_deletion, process_export


@shared_task(name="privacy.process_export", acks_late=True, max_retries=3)
def process_export_task(export_job_id: str) -> str:
    return process_export(export_job_id)


@shared_task(name="privacy.process_deletion", acks_late=True, max_retries=3)
def process_deletion_task(deletion_id: str) -> str:
    return process_deletion(deletion_id)
