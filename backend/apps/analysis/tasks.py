from __future__ import annotations

from celery import shared_task

from .services import run_analysis


@shared_task(name="analysis.run_analysis", acks_late=True, max_retries=3)
def run_analysis_task(job_id: str) -> str:
    """Idempotent: re-running clears prior findings and recomputes them."""
    return run_analysis(job_id)
