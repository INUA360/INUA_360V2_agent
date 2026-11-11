from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.documents.models import Document, DocumentType


class DocumentSerializer(serializers.ModelSerializer[Document]):
    doc_type_label = serializers.CharField(source="get_doc_type_display", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "doc_type",
            "doc_type_label",
            "filename",
            "content_type",
            "size",
            "expiry_date",
            "created_at",
        ]
        read_only_fields = ["id", "filename", "content_type", "size", "created_at"]


class DocumentUploadSerializer(serializers.Serializer[Any]):
    file = serializers.FileField(write_only=True)
    doc_type = serializers.ChoiceField(choices=DocumentType.choices)
    expiry_date = serializers.DateField(required=False, allow_null=True)
