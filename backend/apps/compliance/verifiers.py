"""Compliance verification interface.

Milestone 1 ships only the self-reported implementation. The protocol exists so
GavaConnect can be added without changing serializers, scoring, or UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from django.conf import settings
from django.utils import timezone
from django.utils.module_loading import import_string


@dataclass(frozen=True)
class VerificationResult:
    status: str
    source: str
    checked_at: datetime
    reference: str = ""
    message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class ComplianceVerifier(Protocol):
    def verify_pin(self, pin: str) -> VerificationResult: ...

    def verify_tcc(self, pin: str) -> VerificationResult: ...


class SelfReportedVerifier:
    """No external call. The value and its verification badge are self-reported."""

    def verify_pin(self, pin: str) -> VerificationResult:
        return VerificationResult(
            status="self_reported",
            source="self_reported",
            checked_at=timezone.now(),
            reference=pin,
            message="PIN was entered by the merchant and has not been independently verified.",
        )

    def verify_tcc(self, pin: str) -> VerificationResult:
        return VerificationResult(
            status="self_reported",
            source="self_reported",
            checked_at=timezone.now(),
            reference=pin,
            message="TCC status is self-reported and has not been independently verified.",
        )


class GavaConnectVerifier:
    """Placeholder for the future live KRA GavaConnect integration.

    TODO(owner): supply GavaConnect credentials/approval. Endpoints we will use:
      1. PIN Checker        — verify a KRA PIN belongs to the taxpayer.
      2. TCC Checker        — verify Tax Compliance Certificate validity/expiry.
      3. Taxpayer Obligations — retrieve filing/payment obligation status.

    This class must never be selected in Milestone 1.
    """

    def verify_pin(self, pin: str) -> VerificationResult:
        raise NotImplementedError("GavaConnect integration is not available in Milestone 1.")

    def verify_tcc(self, pin: str) -> VerificationResult:
        raise NotImplementedError("GavaConnect integration is not available in Milestone 1.")


def get_verifier() -> ComplianceVerifier:
    verifier_path = getattr(
        settings, "COMPLIANCE_VERIFIER", "apps.compliance.verifiers.SelfReportedVerifier"
    )
    verifier_cls = import_string(verifier_path)
    return verifier_cls()  # type: ignore[no-any-return]
