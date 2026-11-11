from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.opportunities.models import Opportunity, OpportunityMatch


class OpportunitySerializer(serializers.ModelSerializer[Opportunity]):
    is_stale = serializers.BooleanField(read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            "id",
            "name",
            "provider",
            "provider_type",
            "type",
            "description",
            "min_amount",
            "max_amount",
            "allowed_sectors",
            "counties",
            "min_months_operating",
            "min_readiness_score",
            "required_compliance",
            "required_documents",
            "accepts_informal",
            "application_url",
            "deadline",
            "status",
            "source_url",
            "last_verified_at",
            "is_stale",
            "notes",
        ]
        read_only_fields = fields


class OpportunityMatchSerializer(serializers.ModelSerializer[OpportunityMatch]):
    opportunity = OpportunitySerializer(read_only=True)

    class Meta:
        model = OpportunityMatch
        fields = [
            "id",
            "opportunity",
            "fit_level",
            "explanation",
            "state",
            "computed_at",
        ]
        read_only_fields = ["id", "opportunity", "fit_level", "explanation", "computed_at"]


class MatchStateSerializer(serializers.Serializer[Any]):
    state = serializers.ChoiceField(choices=OpportunityMatch.State.choices)
