"""Create a demo user, workspace, documents and a completed analysis.

Uses only non-personal, fictional sample content. Safe to re-run.
"""
from __future__ import annotations


from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.analysis.models import AnalysisJob
from apps.analysis.services import run_analysis
from apps.documents.services import create_document_from_upload, process_document
from apps.sample_content import SOURCE_TEXT, TARGET_TEXT
from apps.workspaces.models import Membership, Workspace


class Command(BaseCommand):
    help = "Seed a demo workspace with sample documents and run an analysis."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="demo@example.test")
        parser.add_argument("--password", default="demo-pass-12345")

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        email = options["email"]
        user, created = User.objects.get_or_create(email=email)
        if created:
            user.set_password(options["password"])
            user.first_name = "Demo"
            user.save()

        workspace, _ = Workspace.objects.get_or_create(
            slug="demo-workspace", defaults={"name": "Demo Workspace", "created_by": user}
        )
        Membership.objects.get_or_create(workspace=workspace, user=user, defaults={"role": "owner"})

        with transaction.atomic():
            # Reset any prior demo documents/analyses for a clean run.
            workspace.documents.all().delete()
            AnalysisJob.objects.filter(workspace=workspace).delete()

        target = create_document_from_upload(
            workspace=workspace,
            role="target",
            uploaded_file=SimpleUploadedFile("demo-target.txt", TARGET_TEXT.encode(), content_type="text/plain"),
            user=user,
        )
        process_document(target.id)

        source = create_document_from_upload(
            workspace=workspace,
            role="source",
            uploaded_file=SimpleUploadedFile("demo-source.txt", SOURCE_TEXT.encode(), content_type="text/plain"),
            user=user,
        )
        process_document(source.id)

        job = AnalysisJob.objects.create(workspace=workspace, target_document=target, requested_by=user)
        run_analysis(job.id)
        job.refresh_from_db()

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write(f"  Email:     {email}")
        self.stdout.write(f"  Password:  {options['password']}")
        self.stdout.write(f"  Workspace: {workspace.slug} ({workspace.id})")
        self.stdout.write(f"  Analysis:  {job.id} status={job.status} findings={job.findings.count()}")
