from __future__ import annotations

from typing import Any

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    onboarding_percent = serializers.SerializerMethodField()
    email_verified = serializers.BooleanField(source="is_email_verified", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "role",
            "email_verified",
            "consent_version",
            "consent_at",
            "onboarding_step",
            "onboarding_percent",
            "onboarding_completed_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "role",
            "email_verified",
            "consent_version",
            "consent_at",
            "onboarding_completed_at",
            "created_at",
        ]

    def get_onboarding_percent(self, user: User) -> int:
        from apps.businesses.onboarding import onboarding_percent

        return onboarding_percent(user)


class RegisterSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    consent_version = serializers.CharField(max_length=32)
    consent_given = serializers.BooleanField()

    def validate_email(self, value: str) -> str:
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs.get("consent_given"):
            raise serializers.ValidationError(
                {"consent_given": "Consent is required to process financial data."}
            )
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data: dict[str, Any]) -> User:
        from django.utils import timezone

        validated_data.pop("consent_given", None)
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            phone=validated_data.get("phone", ""),
            consent_version=validated_data["consent_version"],
            consent_at=timezone.now(),
        )


class LoginSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"].lower().strip(),
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError({"detail": "Invalid email or password."})
        if not user.is_active:
            raise serializers.ValidationError({"detail": "This account is inactive."})
        attrs["user"] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer[Any]):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value


class VerifyEmailSerializer(serializers.Serializer[Any]):
    token = serializers.CharField()


class MeUpdateSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["phone", "onboarding_step"]

    def validate_onboarding_step(self, value: int) -> int:
        if value < 1 or value > 4:
            raise serializers.ValidationError("Onboarding step must be between 1 and 4.")
        return value
