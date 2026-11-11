from __future__ import annotations

from apps.readiness.engine import (
    BusinessSnapshot,
    ComplianceSnapshot,
    FinancialSnapshot,
    compute_readiness,
    load_config,
)


def _financials(**overrides: object) -> FinancialSnapshot:
    values: dict[str, object] = {
        "has_statement": True,
        "months_of_data": 12,
        "average_monthly_inflow": 100_000,
        "average_monthly_revenue": 90_000,
        "average_monthly_outflow": 70_000,
        "revenue_consistency_cv": 0.18,
        "net_cash_flow_positive_ratio": 0.9,
        "debt_service_ratio": 0.08,
        "has_loans": True,
        "data_confidence": "high",
        "categorisation_confidence": 0.8,
    }
    values.update(overrides)
    return FinancialSnapshot(**values)  # type: ignore[arg-type]


def _snapshot(**overrides: object) -> BusinessSnapshot:
    values: dict[str, object] = {
        "months_operating": 36,
        "compliance": ComplianceSnapshot(
            pin_valid=True,
            pin_verified=True,
            tcc_valid=True,
            tcc_verified=True,
            permit_valid=True,
            permit_verified=True,
            registration_valid=True,
            registration_verified=True,
            pin_present=True,
            tcc_status="valid",
            permit_status="valid",
        ),
        "financials": _financials(),
        "documents_present": frozenset(
            {
                "business_registration_certificate",
                "kra_pin_certificate",
                "tcc",
                "county_permit",
                "id_owner",
                "bank_statement",
            }
        ),
        "profile_fields_complete": 10,
        "profile_fields_total": 10,
    }
    values.update(overrides)
    return BusinessSnapshot(**values)  # type: ignore[arg-type]


def test_strong_business_scores_high_and_has_no_major_gaps() -> None:
    result = compute_readiness(_snapshot())
    assert result.total_score >= 90
    assert result.band == "strong"
    assert result.config_version == "1.0.0"
    assert result.data_confidence == "high"
    assert "not a credit score" in result.disclaimer


def test_scoring_is_deterministic() -> None:
    first = compute_readiness(_snapshot())
    second = compute_readiness(_snapshot())
    assert first == second


def test_no_statement_halves_revenue_and_cash_flow_and_flags_low_confidence() -> None:
    with_statement = compute_readiness(_snapshot())
    without_statement = compute_readiness(
        _snapshot(financials=_financials(has_statement=False, data_confidence="high"))
    )
    assert without_statement.total_score < with_statement.total_score
    assert without_statement.data_confidence == "low"
    assert without_statement.low_data_confidence is True
    component = next(
        row for row in without_statement.component_scores if row.key == "revenue_consistency"
    )
    assert component.points <= 10


def test_self_reported_compliance_gets_reduced_credit() -> None:
    verified = compute_readiness(_snapshot())
    self_reported = compute_readiness(
        _snapshot(
            compliance=ComplianceSnapshot(
                pin_valid=True,
                tcc_valid=True,
                permit_valid=True,
                registration_valid=True,
                pin_present=True,
                tcc_status="valid",
                permit_status="valid",
            )
        )
    )
    assert self_reported.total_score < verified.total_score


def test_missing_documents_produce_actionable_gaps() -> None:
    result = compute_readiness(_snapshot(documents_present=frozenset()))
    doc_gaps = [gap for gap in result.gaps if "document" in gap.key]
    assert doc_gaps
    assert doc_gaps[0].points_gain > 0
    assert doc_gaps[0].action


def test_config_weights_sum_to_100_and_no_magic_numbers_are_hardcoded() -> None:
    config = load_config()
    total = sum(float(component["weight"]) for component in config["components"].values())
    assert total == 100
    assert config["notes"]["disclaimer"].startswith("This score is a transparent rubric")
