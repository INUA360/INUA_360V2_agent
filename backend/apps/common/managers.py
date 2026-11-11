"""Owner-scoped managers (Django-level isolation, layer 2).

Every merchant-facing queryset must start from `Model.objects.for_user(user)`.
Models declare `owner_lookup`, e.g. "owner_id" for Business or
"business__owner_id" for child rows. The linter-style test in
tests/test_query_scoping.py keeps merchant views honest.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from django.db import models

if TYPE_CHECKING:
    from apps.accounts.models import User


class OwnedQuerySet(models.QuerySet[Any]):
    owner_lookup: str = "owner_id"

    def for_user(self, user: User) -> OwnedQuerySet:
        if not getattr(user, "is_authenticated", False):
            return self.none()
        return self.filter(**{self.owner_lookup: user.pk})

    def for_business(self, business: Any) -> OwnedQuerySet:
        lookup = self.owner_lookup
        if lookup == "business_id":
            return self.filter(business_id=business.pk)
        if lookup == "business__owner_id":
            return self.filter(business_id=business.pk)
        if lookup == "owner_id":
            return self.filter(pk=business.pk)
        return self.filter(**{lookup: business.pk})


class OwnedManager(models.Manager.from_queryset(OwnedQuerySet)):  # type: ignore[misc]
    def get_queryset(self) -> OwnedQuerySet:
        queryset = super().get_queryset()
        queryset.owner_lookup = getattr(self.model, "owner_lookup", queryset.owner_lookup)
        return cast(OwnedQuerySet, queryset)

    def for_user(self, user: User) -> OwnedQuerySet:
        return self.get_queryset().for_user(user)

    def for_business(self, business: Any) -> OwnedQuerySet:
        return self.get_queryset().for_business(business)
