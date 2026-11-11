"""Delete-my-data flow: remove stored objects and all merchant records."""

from __future__ import annotations

import logging
from typing import Any

from django.core.files.storage import default_storage
from django.db import transaction

from apps.audit.models import AuditLog
from apps.businesses.models import Business
from apps.documents.models import Document

logger = logging.getLogger(__name__)


@transaction.atomic
def delete_user_data(user: Any) -> None:
    business = Business.objects.for_user(user).first()  # type: ignore[attr-defined]
    if business is not None:
        storage_keys = list(
            Document.objects.filter(business=business).values_list("storage_key", flat=True)
        )
        for key in storage_keys:
            try:
                default_storage.delete(key)
            except Exception:
                # Never block account deletion on a missing storage object.
                logger.warning("Could not delete a stored document during account deletion.")
        AuditLog.objects.filter(business=business).delete()
    AuditLog.objects.filter(actor=user).delete()

    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

        OutstandingToken.objects.filter(user=user).delete()
    except Exception:
        logger.warning("Could not remove outstanding refresh tokens during account deletion.")

    # Cascades remove business, compliance, statements, transactions,
    # pending statements, monthly aggregates, loans, funding need, documents,
    # assessments, matches, and audit rows linked to the business.
    user.delete()
