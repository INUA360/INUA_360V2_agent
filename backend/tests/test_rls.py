from __future__ import annotations

from datetime import date, timedelta

import psycopg
import pytest
from django.db import connections, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.common.tenancy import set_current_user_id


def _app_connection() -> psycopg.Connection:
    settings_dict = connections["default"].settings_dict
    return psycopg.connect(
        dbname=settings_dict["NAME"],
        user=settings_dict["USER"],
        password=settings_dict["PASSWORD"],
        host=settings_dict["HOST"],
        port=settings_dict["PORT"],
        sslmode=settings_dict["OPTIONS"].get("sslmode", "prefer"),
    )


@pytest.mark.isolation
@pytest.mark.django_db(transaction=True)
def test_rls_fails_closed_without_tenant(user) -> None:
    with _app_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM businesses_business")
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT count(*) FROM financials_transaction")
            assert cursor.fetchone()[0] == 0


@pytest.mark.isolation
@pytest.mark.django_db(transaction=True)
def test_rls_isolates_tenants_for_raw_sql(user, tenant) -> None:
    with transaction.atomic():
        set_current_user_id(user.pk)
        Business.objects.create(
            owner=user,
            name="Tenant One",
            sector=Business.Sector.RETAIL,
            what_they_sell="Goods",
            county="Nairobi",
            town="CBD",
            started_on=date.today() - timedelta(days=500),
            structure=Business.Structure.SOLE_PROPRIETOR,
            employee_band=Business.EmployeeBand.ZERO,
            owner_name="Owner One",
            owner_phone="+254700000001",
        )

    other = User.objects.create_user(
        email="raw-other@example.com",
        password="A-strong-pass-123",
        consent_version="m1-v1",
        consent_at=timezone.now(),
    )
    with transaction.atomic():
        set_current_user_id(other.pk)
        Business.objects.create(
            owner=other,
            name="Tenant Two",
            sector=Business.Sector.RETAIL,
            what_they_sell="Goods",
            county="Nairobi",
            town="CBD",
            started_on=date.today() - timedelta(days=500),
            structure=Business.Structure.SOLE_PROPRIETOR,
            employee_band=Business.EmployeeBand.ZERO,
            owner_name="Owner Two",
            owner_phone="+254700000002",
        )

    with _app_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.current_user_id', %s, true)", [str(user.pk)])
            cursor.execute("SELECT name FROM businesses_business")
            assert [row[0] for row in cursor.fetchall()] == ["Tenant One"]
            cursor.execute(
                "UPDATE businesses_business SET name = 'hijacked' WHERE name = 'Tenant Two'"
            )
            assert cursor.rowcount == 0
            cursor.execute("DELETE FROM businesses_business WHERE name = 'Tenant Two'")
            assert cursor.rowcount == 0


@pytest.mark.isolation
@pytest.mark.django_db(transaction=True)
def test_app_role_is_not_owner_or_bypassrls() -> None:
    with _app_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT rolsuper, rolbypassrls, rolcreatedb "
                "FROM pg_roles WHERE rolname = current_user"
            )
            row = cursor.fetchone()
            assert row == (False, False, False)
            cursor.execute(
                """
                SELECT relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname = 'businesses_business'
                """
            )
            assert cursor.fetchone() == (True, True)


@pytest.mark.isolation
@pytest.mark.django_db
def test_tenant_can_insert_only_own_business(user, tenant) -> None:
    tenant(user)
    Business.objects.create(
        owner=user,
        name="Allowed",
        sector=Business.Sector.RETAIL,
        what_they_sell="Goods",
        county="Nairobi",
        town="CBD",
        started_on=date.today() - timedelta(days=100),
        structure=Business.Structure.SOLE_PROPRIETOR,
        employee_band=Business.EmployeeBand.ZERO,
        owner_name="Owner",
        owner_phone="+254700000003",
    )
    assert Business.objects.for_user(user).count() == 1
