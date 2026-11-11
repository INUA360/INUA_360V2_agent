from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.documents.models import Document
from apps.opportunities.models import Opportunity
from apps.readiness.models import ReadinessAssessment


def test_register_sets_consent_and_returns_access_token(api_client, db) -> None:
    response = api_client.post(
        "/api/v1/auth/register",
        {
            "email": "new-merchant@example.com",
            "phone": "+254711000000",
            "password": "A-strong-pass-123",
            "consent_version": "m1-v1",
            "consent_given": True,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["access"]
    assert response.data["user"]["consent_version"] == "m1-v1"
    assert "inua_refresh" in response.cookies
    assert User.objects.filter(email="new-merchant@example.com").exists()


def test_register_requires_consent(api_client, db) -> None:
    response = api_client.post(
        "/api/v1/auth/register",
        {
            "email": "no-consent@example.com",
            "password": "A-strong-pass-123",
            "consent_version": "m1-v1",
            "consent_given": False,
        },
        format="json",
    )
    assert response.status_code == 400
    assert "consent" in str(response.data).lower()


def test_business_get_and_update_scoped_to_owner(auth_client, business) -> None:
    response = auth_client.get("/api/v1/business")
    assert response.status_code == 200
    assert response.data["name"] == "Mama Njeri Grocers"

    response = auth_client.put(
        "/api/v1/business",
        {"town": "Kibera", "what_they_sell": "Groceries, airtime and eggs"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["town"] == "Kibera"


def test_other_merchants_business_is_not_visible(auth_client, business, user, tenant, db) -> None:
    from apps.businesses.models import Business

    other = User.objects.create_user(
        email="other@example.com",
        password="A-strong-pass-123",
        consent_version="m1-v1",
        consent_at=timezone.now(),
    )
    tenant(other)
    Business.objects.create(
        owner=other,
        name="Other Shop",
        sector=Business.Sector.RETAIL,
        what_they_sell="Shoes",
        county="Nairobi",
        town="CBD",
        started_on=date.today() - timedelta(days=400),
        structure=Business.Structure.SOLE_PROPRIETOR,
        employee_band=Business.EmployeeBand.ZERO,
        owner_name="Other Owner",
        owner_phone="+254722000000",
    )
    tenant(user)
    response = auth_client.get("/api/v1/business")
    assert response.status_code == 200
    assert response.data["name"] == "Mama Njeri Grocers"


def test_document_detail_and_download_url_return_404_for_other_tenant(
    auth_client, user, tenant, db
) -> None:
    from apps.businesses.models import Business

    other = User.objects.create_user(
        email="other-docs@example.com",
        password="A-strong-pass-123",
        consent_version="m1-v1",
        consent_at=timezone.now(),
    )
    tenant(other)
    other_business = Business.objects.create(
        owner=other,
        name="Other Docs Shop",
        sector=Business.Sector.RETAIL,
        what_they_sell="Shoes",
        county="Nairobi",
        town="CBD",
        started_on=date.today() - timedelta(days=400),
        structure=Business.Structure.SOLE_PROPRIETOR,
        employee_band=Business.EmployeeBand.ZERO,
        owner_name="Other Owner",
        owner_phone="+254722000000",
    )
    other_document = Document.objects.create(
        business=other_business,
        doc_type="kra_pin_certificate",
        storage_key="private/other.pdf",
        filename="pin.pdf",
        content_type="application/pdf",
        size=1024,
    )
    tenant(user)
    assert auth_client.delete(f"/api/v1/documents/{other_document.pk}").status_code == 404
    assert auth_client.get(f"/api/v1/documents/{other_document.pk}/download-url").status_code == 404
    assert auth_client.get(f"/api/v1/documents/{other_document.pk}/file").status_code == 404


def test_readiness_requires_business_and_recomputes(auth_client, user, tenant, db) -> None:
    response = auth_client.get("/api/v1/readiness")
    assert response.status_code == 404
    assert "business" in response.data["error"]["message"].lower()


def test_readiness_recompute_for_business(auth_client, business) -> None:
    response = auth_client.post("/api/v1/readiness/recompute")
    assert response.status_code == 200
    assert 0 <= response.data["latest"]["total_score"] <= 100
    assert response.data["score_is"] == "rule_based_rubric_not_credit_score"
    assert "not a credit score" in response.data["disclaimer"]
    assert ReadinessAssessment.objects.filter(business=business).exists()


def test_opportunity_matches_are_scoped_and_explainable(auth_client, business, db, tenant) -> None:
    from apps.financials.models import FundingNeed

    tenant(business.owner)
    FundingNeed.objects.create(
        business=business,
        amount=150_000,
        purpose="working_capital",
        timeframe="flexible",
    )
    Opportunity.objects.filter(status="active").update(last_verified_at=timezone.now())
    auth_client.post("/api/v1/readiness/recompute")
    response = auth_client.get("/api/v1/opportunities/matches")
    assert response.status_code == 200
    assert isinstance(response.data, list)
    for row in response.data:
        assert row["fit_level"] in {"strong", "possible", "stretch"}
        assert row["explanation"]["summary"]
        assert row["opportunity"]["name"].startswith("EXAMPLE —")


def test_checklist_is_available_for_opportunity(auth_client, business, db, tenant) -> None:
    tenant(business.owner)
    opportunity = Opportunity.objects.filter(status="active").first()
    assert opportunity is not None
    response = auth_client.get(f"/api/v1/opportunities/{opportunity.pk}/checklist")
    assert response.status_code == 200
    assert response.data["items"]
    assert response.data["opportunity"]["name"].startswith("EXAMPLE —")


@pytest.mark.parametrize("path", ["/api/v1/me", "/api/v1/business", "/api/v1/readiness"])
def test_unauthenticated_requests_are_rejected(api_client, db, path: str) -> None:
    assert api_client.get(path).status_code in {401, 404}


def test_statement_parse_and_confirm_keeps_only_normalized_rows(
    auth_client, business, tenant
) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.financials.models import Transaction
    from apps.ingestion.generator import generate_statement_bytes

    raw = generate_statement_bytes(
        months=2, rows_per_month=5, password="statement-pass", layout="a"
    )
    upload = SimpleUploadedFile("statement.pdf", raw, content_type="application/pdf")
    response = auth_client.post(
        "/api/v1/statements/parse",
        {"file": upload, "password": "statement-pass"},
        format="multipart",
    )
    assert response.status_code == 201
    pending_id = response.data["pending_id"]
    assert response.data["summary"]["rows_parsed"] > 0
    assert response.data["summary"]["preview"][0]["source_ref"]
    assert response.data["summary"]["preview"][0]["amount"]

    confirmed = auth_client.post(f"/api/v1/statements/{pending_id}/confirm", format="json")
    assert confirmed.status_code == 201
    assert confirmed.data["status"] == "confirmed"
    assert confirmed.data["row_count"] > 0
    tenant(business.owner)
    assert Transaction.objects.filter(business=business).count() == confirmed.data["row_count"]
