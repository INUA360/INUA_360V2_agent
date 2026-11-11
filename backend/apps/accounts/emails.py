from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail

from apps.accounts.models import OneTimeToken, User


def send_verification_email(user: User) -> None:
    token = OneTimeToken.issue(user, OneTimeToken.Purpose.EMAIL_VERIFICATION, ttl_minutes=60 * 24)
    link = f"{settings.FRONTEND_ORIGIN}/verify-email?token={token}"
    send_mail(
        subject="Verify your Inua360 email",
        message=f"Confirm your email address to finish setting up Inua360: {link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def send_password_reset_email(user: User) -> None:
    token = OneTimeToken.issue(user, OneTimeToken.Purpose.PASSWORD_RESET, ttl_minutes=60)
    link = f"{settings.FRONTEND_ORIGIN}/reset-password?token={token}"
    send_mail(
        subject="Reset your Inua360 password",
        message=f"Use this single-use link within 60 minutes to reset your password: {link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
