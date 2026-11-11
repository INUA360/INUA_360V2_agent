from __future__ import annotations

from rest_framework import serializers

from apps.readiness.models import ReadinessAssessment


class ReadinessAssessmentSerializer(serializers.ModelSerializer[ReadinessAssessment]):
    class Meta:
        model = ReadinessAssessment
        fields = [
            "id",
            "total_score",
            "band",
            "component_scores",
            "gaps",
            "data_confidence",
            "config_version",
            "computed_at",
        ]
        read_only_fields = fields
