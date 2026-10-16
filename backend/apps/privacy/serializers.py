from __future__ import annotations

from rest_framework import serializers

from .models import DeletionRequest, DeletionScope, ExportJob


class DeletionRequestSerializer(serializers.ModelSerializer):
    scope = serializers.ChoiceField(choices=DeletionScope.choices)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = DeletionRequest
        fields = ["id", "scope", "status", "status_label", "result", "error_message", "created_at", "completed_at"]
        read_only_fields = ["id", "status", "result", "error_message", "created_at", "completed_at"]


class ExportJobSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = ExportJob
        fields = [
            "id", "status", "status_label", "size_bytes", "is_expired",
            "error_message", "created_at", "completed_at", "expires_at",
        ]
        read_only_fields = fields
