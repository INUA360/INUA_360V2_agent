from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal, cast

from django.conf import settings
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts import emails
from apps.accounts.models import OneTimeToken, User
from apps.accounts.serializers import (
    LoginSerializer,
    MeUpdateSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)
from apps.common.mixins import MerchantAPIView, no_content


def _set_refresh_cookie(response: Response, refresh: RefreshToken) -> None:
    lifetime = cast(timedelta, settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"])
    max_age = int(lifetime.total_seconds())
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        str(refresh),
        max_age=max_age,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=cast(Literal["Lax", "Strict", "None", False], settings.REFRESH_COOKIE_SAMESITE),
        path=settings.REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        samesite=cast(Literal["Lax", "Strict", "None", False], settings.REFRESH_COOKIE_SAMESITE),
    )


def _auth_payload(user: User) -> dict[str, Any]:
    refresh = RefreshToken.for_user(user)
    return {"refresh": refresh, "access": str(refresh.access_token)}


class CsrfTokenView(APIView):
    permission_classes = [AllowAny]
    throttle_classes: list[type] = []

    @method_decorator(ensure_csrf_cookie)
    def get(self, request: Any) -> Response:
        return Response({"csrfToken": get_token(request)})


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request: Any) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        emails.send_verification_email(user)
        tokens = _auth_payload(user)
        response = Response(
            {"user": UserSerializer(user).data, "access": tokens["access"]},
            status=status.HTTP_201_CREATED,
        )
        _set_refresh_cookie(response, tokens["refresh"])
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Any) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = _auth_payload(user)
        response = Response({"user": UserSerializer(user).data, "access": tokens["access"]})
        _set_refresh_cookie(response, tokens["refresh"])
        return response


@method_decorator(csrf_protect, name="dispatch")
class RefreshView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Any) -> Response:
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw:
            return Response(
                {"error": {"code": "no_refresh_token", "message": "Not authenticated."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            refresh = RefreshToken(raw)
        except TokenError:
            response = Response(
                {"error": {"code": "invalid_refresh_token", "message": "Session expired."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _clear_refresh_cookie(response)
            return response

        user_id = refresh.get("user_id")
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            response = Response(
                {"error": {"code": "invalid_refresh_token", "message": "Session expired."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _clear_refresh_cookie(response)
            return response

        access = str(refresh.access_token)
        # Rotation: blacklist old token, issue a new refresh token.
        try:
            refresh.blacklist()
        except AttributeError:
            pass
        new_refresh = RefreshToken.for_user(user)
        response = Response({"access": access, "user": UserSerializer(user).data})
        _set_refresh_cookie(response, new_refresh)
        return response


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Any) -> Response:
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        response = no_content()
        _clear_refresh_cookie(response)
        return response


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Any) -> Response:
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = OneTimeToken.consume(
            serializer.validated_data["token"], OneTimeToken.Purpose.EMAIL_VERIFICATION
        )
        if token is None:
            return Response(
                {"error": {"code": "invalid_token", "message": "This link is invalid or expired."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token.user.email_verified_at = timezone.now()
        token.user.save(update_fields=["email_verified_at", "updated_at"])
        return Response({"detail": "Email verified."})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Any) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"].lower()).first()
        if user:
            emails.send_password_reset_email(user)
        # Do not reveal whether the email exists.
        return Response({"detail": "If that account exists, a reset email has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Any) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = OneTimeToken.consume(
            serializer.validated_data["token"], OneTimeToken.Purpose.PASSWORD_RESET
        )
        if token is None:
            return Response(
                {"error": {"code": "invalid_token", "message": "This link is invalid or expired."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token.user.set_password(serializer.validated_data["new_password"])
        token.user.save(update_fields=["password", "updated_at"])
        return Response({"detail": "Password updated."})


class MeView(MerchantAPIView):
    def get(self, request: Any) -> Response:
        return Response(UserSerializer(request.user).data)

    def put(self, request: Any) -> Response:
        serializer = MeUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        if user.onboarding_step >= 4 and user.onboarding_completed_at is None:
            from apps.businesses.onboarding import is_onboarding_complete

            if is_onboarding_complete(user):
                user.onboarding_completed_at = timezone.now()
                user.save(update_fields=["onboarding_completed_at", "updated_at"])
        return Response(UserSerializer(user).data)


class DeleteMyDataView(MerchantAPIView):
    """Delete the merchant account and every piece of merchant data."""

    def delete(self, request: Any) -> Response:
        from apps.accounts.deletion import delete_user_data

        delete_user_data(request.user)
        response = no_content()
        _clear_refresh_cookie(response)
        return response
