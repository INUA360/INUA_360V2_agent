from __future__ import annotations

from django.db import models

from apps.common.managers import OwnedManager
from apps.common.models import UUIDModel


class DocumentType(models.TextChoices):
    REGISTRATION_CERTIFICATE = (
        "business_registration_certificate",
        "Business registration certificate",
    )
    KRA_PIN_CERTIFICATE = "kra_pin_certificate", "KRA PIN certificate"
    TCC = "tcc", "Tax Compliance Certificate"
    COUNTY_PERMIT = "county_permit", "County business permit"
    ID_OWNER = "id_owner", "Owner ID"
    BUSINESS_PLAN = "business_plan", "Business plan"
    BANK_STATEMENT = "bank_statement", "Bank statement"
    LEASE = "lease_premises", "Lease / premises proof"
    OTHER = "other", "Other"


STANDARD_DOCUMENT_TYPES = [
    DocumentType.REGISTRATION_CERTIFICATE,
    DocumentType.KRA_PIN_CERTIFICATE,
    DocumentType.TCC,
    DocumentType.COUNTY_PERMIT,
    DocumentType.ID_OWNER,
    DocumentType.BANK_STATEMENT,
]


class Document(UUIDModel):
    business = models.ForeignKey(
        "businesses.Business", on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(max_length=48, choices=DocumentType.choices)
    storage_key = models.CharField(max_length=512)
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    size = models.PositiveIntegerField()
    expiry_date = models.DateField(null=True, blank=True)

    objects = OwnedManager()
    owner_lookup = "business__owner_id"

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.doc_type}: {self.filename}"
