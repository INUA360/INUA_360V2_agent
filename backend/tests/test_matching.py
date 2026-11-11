from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from apps.opportunities.matching import MatchSnapshot, OpportunityData, match


def _opportunity(**overrides: object) -> OpportunityData:
    values: dict[str, object] = {
        "id": "opp-1",
        "name": "EXAMPLE — Working capital line",
        "provider": "EXAMPLE — Partner",
        "provider_type": "bank",
        "type": "loan",
        "min_amount": Decimal("50000"),
        "max_amount": Decimal("500000"),
        "allowed_sectors": ("retail",),
        "counties": ("Nairobi",),
        "min_months_operating": 12,
        "min_readiness_score": 60,
        "required_compliance": ("pin", "tcc"),
        "required_documents": ("kra_pin_certificate", "tcc"),
        "accepts_informal": True,
        "description": "Example product for tests.",
    }
    values.update(overrides)
    return OpportunityData(**values)  # type: ignore[arg-type]


def _snapshot(**overrides: object) -> MatchSnapshot:
    values: dict[str, object] = {
        "sector": "retail",
        "county": "Nairobi",
        "structure": "sole_proprietor",
        "months_operating": 24,
        "requested_amount": Decimal("200000"),
        "readiness_score": 80,
        "pin_valid": True,
        "tcc_valid": True,
        "permit_valid": True,
        "registration_valid": True,
        "documents_present": frozenset({"kra_pin_certificate", "tcc"}),
        "today": date(2026, 11, 1),
    }
    values.update(overrides)
    return MatchSnapshot(**values)  # type: ignore[arg-type]


def test_all_requirements_met_is_strong() -> None:
    results = match(_snapshot(), [_opportunity()])
    assert len(results) == 1
    assert results[0].fit_level == "strong"
    assert not results[0].missing
    assert "Meets all listed requirements" in results[0].explanation["summary"]


def test_missing_requirements_are_explained_with_actions() -> None:
    results = match(
        _snapshot(tcc_valid=False, documents_present=frozenset()),
        [_opportunity()],
    )
    assert len(results) == 1
    assert results[0].fit_level in {"possible", "stretch"}
    missing_keys = {item.key for item in results[0].missing}
    assert "compliance:tcc" in missing_keys
    assert "document:tcc" in missing_keys
    assert results[0].moves_to_strong


def test_hard_filters_remove_ineligible_opportunities() -> None:
    assert match(_snapshot(sector="tech"), [_opportunity()]) == []
    assert match(_snapshot(county="Kisumu"), [_opportunity()]) == []
    assert match(_snapshot(requested_amount=Decimal("9000000")), [_opportunity()]) == []


def test_expired_deadline_and_inactive_listing_are_excluded() -> None:
    expired = _opportunity(deadline=date(2026, 10, 1))
    inactive = _opportunity(status="closed")
    assert match(_snapshot(), [expired, inactive]) == []


def test_future_deadline_is_kept_and_results_are_ordered() -> None:
    soon = _opportunity(id="soon", name="EXAMPLE — Soon", deadline=date(2026, 12, 1))
    later = _opportunity(
        id="later",
        name="EXAMPLE — Later",
        deadline=date(2026, 12, 31),
        min_amount=Decimal("50000"),
        max_amount=Decimal("500000"),
    )
    results = match(_snapshot(), [later, soon])
    assert [row.opportunity_id for row in results] == ["soon", "later"]


def test_informal_structure_is_noted_for_formal_only_products() -> None:
    results = match(
        _snapshot(structure="sole_proprietor"),
        [_snapshot_product()],
    )
    assert results[0].fit_level != "strong"
    assert any(item.key == "formal_structure" for item in results[0].missing)


def test_score_gap_is_reported() -> None:
    results = match(
        _snapshot(readiness_score=40),
        [_opportunity(min_readiness_score=70)],
    )
    assert results[0].explanation["score_gap"] == 30
    assert any(item.key == "readiness_score" for item in results[0].missing)


def test_stale_by_deadline_cutoff_uses_snapshot_clock() -> None:
    product = _opportunity(deadline=date.today() + timedelta(days=1))
    assert match(_snapshot(today=date.today()), [product])


def _snapshot_product() -> OpportunityData:
    return _opportunity(accepts_informal=False)
