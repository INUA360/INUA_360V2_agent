from __future__ import annotations

import os
import re
import uuid
from typing import Any, cast

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.documents.models import STANDARD_DOCUMENT_TYPES, Document, DocumentType

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
PDF_MAGIC = b"%PDF-"
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename or "document")
    base = base.replace("\x00", "")
    base = SAFE_NAME_RE.sub("_", base).strip("._")
    if not base:
        base = "document"
    return base[:120]


def sniff_content_type(head: bytes) -> str | None:
    if head.startswith(PDF_MAGIC):
        return "application/pdf"
    if head.startswith(JPEG_MAGIC):
        return "image/jpeg"
    if head.startswith(PNG_MAGIC):
        return "image/png"
    return None


def storage_key(user_id: Any, business_id: Any, doc_type: str, filename: str) -> str:
    return f"{user_id}/{business_id}/{doc_type}/{uuid.uuid4()}-{filename}"


def upload_document(
    business: Any,
    user: Any,
    doc_type: str,
    uploaded_file: Any,
    expiry_date: Any = None,
) -> Document:
    if doc_type not in DocumentType.values:
        raise ValidationError({"doc_type": "Choose a valid document type."})
    if uploaded_file.size > settings.DOCUMENT_MAX_BYTES:
        raise ValidationError({"file": "File must be 10 MB or smaller."})
    head = uploaded_file.read(16)
    uploaded_file.seek(0)
    content_type = sniff_content_type(head)
    if content_type is None:
        raise ValidationError({"file": "Upload a PDF, JPG, or PNG file."})
    if uploaded_file.size == 0:
        raise ValidationError({"file": "The uploaded file is empty."})

    filename = sanitize_filename(uploaded_file.name)
    key = storage_key(user.pk, business.pk, doc_type, filename)
    saved_key = default_storage.save(key, uploaded_file)
    try:
        document = Document.objects.create(
            business=business,
            doc_type=doc_type,
            storage_key=saved_key,
            filename=filename,
            content_type=content_type,
            size=uploaded_file.size,
            expiry_date=expiry_date,
        )
    except Exception:
        default_storage.delete(saved_key)
        raise
    return cast(Document, document)


def delete_document(document: Document) -> None:
    try:
        default_storage.delete(document.storage_key)
    finally:
        document.delete()


def signed_download_url(document: Document) -> tuple[str, int]:
    ttl = settings.STORAGE_SIGNED_URL_TTL_SECONDS
    if settings.STORAGE_BACKEND == "s3":
        url = default_storage.url(  # type: ignore[call-arg]
            document.storage_key,
            parameters={
                "ResponseContentDisposition": (
                    f'attachment; filename="{sanitize_filename(document.filename)}"'
                )
            },
            expire=ttl,
        )
        return url, ttl
    # Local development: stream through Django, never expose the filesystem path.
    return f"/api/v1/documents/{document.pk}/file", ttl


def open_document(document: Document) -> FileResponse:
    if not default_storage.exists(document.storage_key):
        raise NotFound("The stored file is missing.")
    handle = default_storage.open(document.storage_key, "rb")
    return FileResponse(
        handle,
        as_attachment=True,
        filename=document.filename,
        content_type=document.content_type,
    )


def checklist(business: Any) -> list[dict[str, Any]]:
    present = set(Document.objects.filter(business=business).values_list("doc_type", flat=True))
    return [
        {
            "doc_type": doc_type,
            "label": DocumentType(doc_type).label,
            "present": doc_type in present,
        }
        for doc_type in STANDARD_DOCUMENT_TYPES
    ]


def expire_passed_documents(business: Any) -> None:
    """Metadata-only helper; expiry is surfaced in the UI, not auto-deleted."""
    today = timezone.localdate()
    Document.objects.filter(business=business, expiry_date__lt=today).values_list("id", flat=True)
