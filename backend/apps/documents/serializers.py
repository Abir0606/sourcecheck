from __future__ import annotations

from rest_framework import serializers

from apps.common.constants import DocumentRole, DocumentStatus

from .models import Document, Passage


class DocumentSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "role", "role_label", "original_filename", "content_type",
            "size_bytes", "sha256", "status", "status_label", "stage_detail",
            "page_count", "char_count", "language", "ocr_used",
            "error_code", "error_message", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_created_by(self, obj):
        return obj.created_by.display_name if obj.created_by_id else None


class DocumentUploadSerializer(serializers.Serializer):
    # Empty files are allowed through the field so the view can return a
    # specific error code ("empty_file") from the extraction validator.
    file = serializers.FileField(allow_empty_file=True)
    role = serializers.ChoiceField(choices=DocumentRole.choices)

    def validate_file(self, value):
        return value


class PassageSerializer(serializers.ModelSerializer):
    document_id = serializers.UUIDField(read_only=True)
    filename = serializers.CharField(source="document.original_filename", read_only=True)

    class Meta:
        model = Passage
        fields = ["id", "document_id", "filename", "page_number", "chunk_index", "text"]


class DocumentStatusSerializer(serializers.ModelSerializer):
    """Lightweight status payload for polling."""

    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Document
        fields = ["id", "status", "status_label", "stage_detail", "error_code", "error_message"]


__all__ = [
    "DocumentSerializer",
    "DocumentUploadSerializer",
    "PassageSerializer",
    "DocumentStatusSerializer",
    "DocumentStatus",
]
