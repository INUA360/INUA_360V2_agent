"""Shared pytest fixtures.

The test database is created and migrated as inua_migrator, then the ORM is
switched to inua_app for the test session so row-level security is exercised
with the same non-owner role used in production. RLS is FORCEd even for the
owner, so tenant tests still fail closed if a policy is missing.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any

import pytest
from django.conf import settings
from django.db import connections
from django.test.utils import setup_databases, teardown_databases
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.common.tenancy import clear_current_user_id, set_current_user_id


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker: Any) -> Iterator[None]:
    default = settings.DATABASES["default"]
    migrator = settings.DATABASES["migrator"]
    app_credentials = (default["USER"], default["PASSWORD"])
    migrator_credentials = (migrator["USER"], migrator["PASSWORD"])

    default["USER"], default["PASSWORD"] = migrator_credentials
    saved_migrator = settings.DATABASES.pop("migrator", None)
    with django_db_blocker.unblock():
        old_config = setup_databases(verbosity=0, interactive=False)
        # Test-only: pytest-django flushes with TRUNCATE between transaction
        # tests. The runtime role deliberately does not get this in production.
        with connections["default"].cursor() as cursor:
            cursor.execute("GRANT TRUNCATE ON ALL TABLES IN SCHEMA public TO inua_app")

    for connection in connections.all(initialized_only=True):
        connection.close()
        connection.settings_dict["USER"], connection.settings_dict["PASSWORD"] = app_credentials

    from django.core.management import call_command

    with django_db_blocker.unblock():
        call_command("seed_opportunities", verbosity=0)

    try:
        yield
    finally:
        for connection in connections.all(initialized_only=True):
            connection.close()
            connection.settings_dict["USER"], connection.settings_dict["PASSWORD"] = (
                migrator_credentials
            )
        with django_db_blocker.unblock():
            teardown_databases(old_config, verbosity=0)
        if saved_migrator is not None:
            settings.DATABASES["migrator"] = saved_migrator


@pytest.fixture
def tenant() -> Iterator[Any]:
    def activate(user: User | uuid.UUID | str | None) -> None:
        if isinstance(user, User):
            set_current_user_id(user.pk)
        else:
            set_current_user_id(user)

    yield activate
    clear_current_user_id()


@pytest.fixture
def user(db: Any, tenant: Any) -> User:
    row = User.objects.create_user(
        email=f"merchant-{uuid.uuid4().hex[:10]}@example.com",
        password="Str0ng-Test-Pass-123",
        phone="+254700000001",
        consent_version="test-v1",
        consent_at=timezone.now(),
    )
    tenant(row)
    return row


@pytest.fixture
def business(user: User, tenant: Any) -> Business:
    tenant(user)
    return Business.objects.create(
        owner=user,
        name="Mama Njeri Grocers",
        trading_name="Njeri's",
        sector=Business.Sector.RETAIL,
        what_they_sell="Groceries and household goods",
        county="Nairobi",
        town="Kawangware",
        started_on=date.today() - timedelta(days=900),
        structure=Business.Structure.SOLE_PROPRIETOR,
        employee_band=Business.EmployeeBand.ONE_TO_FIVE,
        owner_name="Njeri Wambui",
        owner_phone="+254700000001",
    )


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def auth_client(api_client: APIClient, user: User) -> APIClient:
    api_client.force_authenticate(user=user)
    return api_client
