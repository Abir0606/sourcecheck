from __future__ import annotations

import hashlib
import io
import logging
import uuid

from django.db import transaction

from apps.common.adapters import get_embedder, get_ocr, get_storage
from apps.common.constants import DocumentStatus

from .extraction import ExtractionError, chunk_pages, extract, validate_upload
from .models import Document, DocumentPage, Passage, document_storage_key

logger = logging.getLogger("apps.documents")


def create_document_from_upload(*, workspace, role: str, uploaded_file, user) -> Document:
    """Validate, hash, store, and persist a Document (status=uploaded)."""
    data = uploaded_file.read()
    fileobj = io.BytesIO(data)
    validate_upload(fileobj=fileobj, filename=uploaded_file.name, declared_type=uploaded_file.content_type)
    sha256 = hashlib.sha256(data).hexdigest()

    document_id = uuid.uuid4()
    key = document_storage_key(workspace.id, document_id, uploaded_file.name)
    get_storage().save(key, io.BytesIO(data))

    document = Document.objects.create(
        id=document_id,
        workspace=workspace,
        role=role,
        original_filename=uploaded_file.name[:512],
        content_type=uploaded_file.content_type or "",
        size_bytes=len(data),
        sha256=sha256,
        storage_key=key,
        status=DocumentStatus.UPLOADED,
        created_by=user,
    )
    return document


def process_document(document_id) -> str:
    """
    Extract text, chunk into passages, and embed. Idempotent: safe to retry.
    Returns the final status.
    """
    document = Document.objects.select_related("workspace").get(pk=document_id)

    if document.status == DocumentStatus.READY:
        return document.status

    storage = get_storage()
    ocr = get_ocr()

    try:
        _set_status(document, DocumentStatus.VALIDATING)
        with storage.open(document.storage_key) as fileobj:
            data = fileobj.read()
        result = extract(
            io.BytesIO(data),
            filename=document.original_filename,
            content_type=document.content_type,
            ocr=ocr,
        )

        if not any((text or "").strip() for _, text in result.pages):
            _set_status(document, DocumentStatus.EMPTY, "No extractable text found.")
            return document.status

        _set_status(document, DocumentStatus.CHUNKING)
        passages = chunk_pages(result.pages)

        with transaction.atomic():
            document.pages.all().delete()
            document.passages.all().delete()
            DocumentPage.objects.bulk_create(
                [
                    DocumentPage(
                        document=document,
                        page_number=pno,
                        text=text or "",
                        char_count=len((text or "").strip()),
                    )
                    for pno, text in result.pages
                ]
            )
            passage_objs = [
                Passage(
                    workspace_id=document.workspace_id,
                    document=document,
                    page_number=p["page_number"],
                    chunk_index=p["chunk_index"],
                    text=p["text"],
                    start_char=p["start_char"],
                    end_char=p["end_char"],
                    token_count=p["token_count"],
                )
                for p in passages
            ]
            Passage.objects.bulk_create(passage_objs)

            _set_status(document, DocumentStatus.EMBEDDING)
            embedder = get_embedder()
            batch = 64
            for start in range(0, len(passage_objs), batch):
                chunk = passage_objs[start : start + batch]
                vectors = embedder.embed([p.text for p in chunk])
                for p, vec in zip(chunk, vectors):
                    p.embedding = vec
                Passage.objects.bulk_update(chunk, ["embedding"])

            document.page_count = len(result.pages)
            document.char_count = sum(len((t or "").strip()) for _, t in result.pages)
            document.ocr_used = result.ocr_used
            document.status = DocumentStatus.READY
            document.stage_detail = ""
            document.error_code = ""
            document.error_message = ""
            document.save(
                update_fields=[
                    "page_count", "char_count", "ocr_used", "status",
                    "stage_detail", "error_code", "error_message", "updated_at",
                ]
            )

        logger.info(
            "document.processed",
            extra={"context": {"document_id": str(document.id), "passages": len(passage_objs)}},
        )
        return document.status

    except ExtractionError as exc:
        _set_status(document, DocumentStatus.FAILED, exc.message, error_code=exc.code)
        logger.warning(
            "document.extraction_failed",
            extra={"context": {"document_id": str(document.id), "code": exc.code}},
        )
        return document.status
    except Exception as exc:  # noqa: BLE001
        _set_status(document, DocumentStatus.FAILED, "Processing failed.", error_code="processing_error")
        logger.exception("document.processing_error", exc_info=exc)
        return document.status


def _set_status(document: Document, status: str, detail: str = "", error_code: str = "") -> None:
    document.status = status
    document.stage_detail = detail[:200]
    document.error_code = error_code
    if status == DocumentStatus.FAILED:
        document.error_message = detail[:500]
    document.save(
        update_fields=["status", "stage_detail", "error_code", "error_message", "updated_at"]
    )
