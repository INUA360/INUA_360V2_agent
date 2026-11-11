"""Object-level permissions used by every protected endpoint."""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission


class IsMerchant(BasePermission):
    message = "Only merchant accounts can access this resource."

    def has_permission(self, request: Any, view: Any) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "role", None) == "merchant")


class IsBusinessOwner(BasePermission):
    """Fallback object check; views also scope querysets and return 404."""

    message = "Not found."

    def has_object_permission(self, request: Any, view: Any, obj: Any) -> bool:
        user = request.user
        business = getattr(obj, "business", None)
        if business is not None:
            return bool(business.owner_id == user.pk)
        if hasattr(obj, "owner_id"):
            return bool(obj.owner_id == user.pk)
        return False
