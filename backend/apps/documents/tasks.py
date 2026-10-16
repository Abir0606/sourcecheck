from __future__ import annotations

from celery import shared_task

from .services import process_document


@shared_task(name="documents.process_document", acks_late=True, max_retries=3)
def process_document_task(document_id: str) -> str:
    """Idempotent: re-running is safe and simply re-derives pages/passages."""
    return process_document(document_id)
