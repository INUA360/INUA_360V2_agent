from __future__ import annotations

from datetime import date, timedelta

from django.db import models
from django.utils import timezone

from apps.common.managers import OwnedManager
from apps.common.models import UUIDModel


class VerificationStatus(models.TextChoices):
    SELF_REPORTED = "self_reported", "Self-reported"
    VERIFIED = "verified", "Verified"


class BusinessCompliance(UUIDModel):
    class RegistrationStatus(models.TextChoices):
        REGISTERED = "registered", "Registered"
        NOT_REGISTERED = "not_registered", "Not registered"
        UNKNOWN = "unknown", "Unknown"

    class PinStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        UNKNOWN = "unknown", "Unknown"

    class TccStatus(models.TextChoices):
        VALID = "valid", "Valid"
        EXPIRED = "expired", "Expired"
        NONE = "none", "None"

    business = models.OneToOneField(
        "businesses.Business", on_delete=models.CASCADE, related_name="compliance"
    )
    registration_status = models.CharField(
        max_length=20, choices=RegistrationStatus.choices, default=RegistrationStatus.UNKNOWN
    )
    registration_number = models.CharField(max_length=80, blank=True)
    kra_pin = models.CharField(max_length=11, blank=True)
    pin_status = models.CharField(
        max_length=20, choices=PinStatus.choices, default=PinStatus.UNKNOWN
    )
    tcc_status = models.CharField(max_length=20, choices=TccStatus.choices, default=TccStatus.NONE)
    tcc_expiry = models.DateField(null=True, blank=True)
    county_permit_number = models.CharField(max_length=80, blank=True)
    county_permit_expiry = models.DateField(null=True, blank=True)
    other_permits = models.JSONField(default=list, blank=True)

    registration_verification = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.SELF_REPORTED
    )
    kra_pin_verification = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.SELF_REPORTED
    )
    tcc_verification = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.SELF_REPORTED
    )
    permit_verification = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.SELF_REPORTED
    )

    objects = OwnedManager()
    owner_lookup = "business__owner_id"

    class Meta:
        verbose_name_plural = "business compliance records"

    def __str__(self) -> str:
        return f"Compliance for {self.business.name}"

    @property
    def tcc_effective_status(self) -> str:
        if self.tcc_status != self.TccStatus.VALID:
            return self.tcc_status
        if self.tcc_expiry and self.tcc_expiry < timezone.localdate():
            return self.TccStatus.EXPIRED
        return self.TccStatus.VALID

    @property
    def tcc_days_remaining(self) -> int | None:
        if not self.tcc_expiry:
            return None
        return (self.tcc_expiry - timezone.localdate()).days

    @property
    def permit_effective_status(self) -> str:
        if not self.county_permit_expiry:
            return "none"
        today: date = timezone.localdate()
        if self.county_permit_expiry < today:
            return "expired"
        if self.county_permit_expiry <= today + timedelta(days=60):
            return "expiring_soon"
        return "valid"

    def has_valid_pin(self) -> bool:
        return bool(self.kra_pin) and self.pin_status == self.PinStatus.ACTIVE

    def has_valid_tcc(self) -> bool:
        return self.tcc_effective_status == self.TccStatus.VALID

    def has_valid_permit(self) -> bool:
        return self.permit_effective_status == "valid"

    def is_registered(self) -> bool:
        return self.registration_status == self.RegistrationStatus.REGISTERED and bool(
            self.registration_number
        )
