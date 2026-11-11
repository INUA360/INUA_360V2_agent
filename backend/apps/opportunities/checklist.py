"""Per-opportunity application checklist (pure)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.opportunities.matching import (
    COMPLIANCE_LABELS,
    DOCUMENT_LABELS,
    MatchSnapshot,
    OpportunityData,
)

FIX_PATHS = {
    "pin": "/onboarding/compliance",
    "tcc": "/onboarding/compliance",
    "permit": "/onboarding/compliance",
    "registration": "/onboarding/compliance",
    "readiness_score": "/dashboard",
    "operating_months": "/onboarding/business",
}
DOC_FIX_PATH = "/documents"


@dataclass(frozen=True)
class ChecklistItem:
    key: str
    label: str
    status: str
    detail: str
    fix_path: str


def build_checklist(snapshot: MatchSnapshot, opportunity: OpportunityData) -> dict[str, Any]:
    items: list[ChecklistItem] = []

    if opportunity.min_readiness_score > 0:
        met = snapshot.readiness_score >= opportunity.min_readiness_score
        items.append(
            ChecklistItem(
                key="readiness_score",
                label="Readiness score",
                status="done" if met else "missing",
                detail=(f"{snapshot.readiness_score} / {opportunity.min_readiness_score} required"),
                fix_path=FIX_PATHS["readiness_score"],
            )
        )
    if opportunity.min_months_operating > 0:
        met = snapshot.months_operating >= opportunity.min_months_operating
        items.append(
            ChecklistItem(
                key="operating_months",
                label="Operating history",
                status="done" if met else "missing",
                detail=(
                    f"{snapshot.months_operating} months / "
                    f"{opportunity.min_months_operating} required"
                ),
                fix_path=FIX_PATHS["operating_months"],
            )
        )

    validity = {
        "pin": snapshot.pin_valid,
        "tcc": snapshot.tcc_valid,
        "permit": snapshot.permit_valid,
        "registration": snapshot.registration_valid,
    }
    for flag in opportunity.required_compliance:
        met = validity.get(flag, False)
        items.append(
            ChecklistItem(
                key=f"compliance:{flag}",
                label=COMPLIANCE_LABELS.get(flag, flag),
                status="done" if met else "missing",
                detail="Provided." if met else "Add this in Compliance.",
                fix_path=FIX_PATHS.get(flag, "/onboarding/compliance"),
            )
        )

    for doc_type in opportunity.required_documents:
        met = doc_type in snapshot.documents_present
        items.append(
            ChecklistItem(
                key=f"document:{doc_type}",
                label=DOCUMENT_LABELS.get(doc_type, doc_type),
                status="done" if met else "missing",
                detail="Uploaded." if met else "Upload this document.",
                fix_path=DOC_FIX_PATH,
            )
        )

    done = sum(1 for item in items if item.status == "done")
    total = len(items)
    return {
        "opportunity": {
            "id": opportunity.id,
            "name": opportunity.name,
            "provider": opportunity.provider,
            "application_url": opportunity.application_url,
            "description": opportunity.description,
        },
        "items": [
            {
                "key": item.key,
                "label": item.label,
                "status": item.status,
                "detail": item.detail,
                "fix_path": item.fix_path,
            }
            for item in items
        ],
        "requirements_met": done,
        "requirements_total": total,
        "summary": f"{done} of {total} requirements met",
    }
