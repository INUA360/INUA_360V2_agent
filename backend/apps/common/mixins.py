"""Base DRF mixins: RLS context, scoped lookup, and merchant-only access."""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsMerchant
from apps.common.tenancy import set_current_user_id


class RLSContextMixin:
    """Set the transaction-local RLS tenant after authentication.

    This is the single hook used by every merchant API view. It runs after
    DRF authentication (super().initial) and before the handler queries data.
    Unauthenticated requests never set a tenant, so RLS policies fail closed.
    """

    def initial(self, request: Any, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)  # type: ignore[misc]
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            set_current_user_id(user.pk)


class MerchantAPIView(RLSContextMixin, APIView):
    permission_classes = [IsAuthenticated, IsMerchant]


class ScopedModelViewMixin:
    """Force detail lookups through an owner-scoped queryset.

    Subclasses set `model` and optionally `owner_lookup`/`queryset`.
    Missing rows return 404 (never 403) so resource existence is not leaked.
    """

    model: Any = None
    request: Any
    kwargs: dict[str, Any]

    def check_object_permissions(self, request: Any, obj: Any) -> None: ...

    def get_queryset(self) -> Any:
        user = self.request.user
        return self.model.objects.for_user(user)  # type: ignore[attr-defined]

    def get_object(self) -> Any:
        pk = self.kwargs.get("pk")
        try:
            obj = self.get_queryset().get(pk=pk)
        except (self.model.DoesNotExist, ValueError):  # type: ignore[union-attr]
            raise NotFound("Not found.") from None
        self.check_object_permissions(self.request, obj)
        return obj


class LatestBusinessMixin:
    """Resolve the authenticated merchant's single business."""

    def get_business(self) -> Any:
        from apps.businesses.models import Business

        business = Business.objects.for_user(self.request.user).first()  # type: ignore[attr-defined]
        if business is None:
            raise NotFound("Create a business profile first.")
        return business


def no_content() -> Response:
    return Response(status=status.HTTP_204_NO_CONTENT)
