from __future__ import annotations

from typing import Any

from django.conf import settings
from rest_framework import serializers

from apps.ingestion.models import PendingStatement, Statement


class StatementParseSerializer(serializers.Serializer[Any]):
    file = serializers.FileField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        max_length=128,
    )

    def validate_file(self, value):  # type: ignore[no-untyped-def]
        if value.size > settings.STATEMENT_MAX_BYTES:
            raise serializers.ValidationError("Statement must be 10 MB or smaller.")
        return value


class StatementSerializer(serializers.ModelSerializer[Statement]):
    class Meta:
        model = Statement
        fields = [
            "id",
            "source",
            "period_start",
            "period_end",
            "row_count",
            "warnings",
            "parse_metadata",
            "status",
            "created_at",
        ]


class PendingStatementPreviewSerializer(serializers.ModelSerializer[PendingStatement]):
    pending_id = serializers.UUIDField(source="id", read_only=True)
    summary = serializers.JSONField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = PendingStatement
        fields = ["pending_id", "summary", "expires_at"]
