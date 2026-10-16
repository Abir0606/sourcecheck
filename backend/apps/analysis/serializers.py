from __future__ import annotations

from rest_framework import serializers

from apps.common.constants import FINDING_STATUS_DESCRIPTIONS, ReviewState

from .models import AnalysisJob, Finding, FindingEvidence, WritingSuggestion


class AnalysisJobSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    stage_label = serializers.CharField(source="get_stage_display", read_only=True)
    target_document_id = serializers.UUIDField(read_only=True)
    target_filename = serializers.CharField(source="target_document.original_filename", read_only=True)

    class Meta:
        model = AnalysisJob
        fields = [
            "id", "target_document_id", "target_filename", "status", "status_label",
            "stage", "stage_label", "progress", "total_claims", "processed_claims",
            "error_code", "error_message", "created_at", "started_at", "finished_at",
        ]


class CreateAnalysisSerializer(serializers.Serializer):
    target_document_id = serializers.UUIDField()
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128)


class FindingEvidenceSerializer(serializers.ModelSerializer):
    filename = serializers.CharField(source="source_document.original_filename", read_only=True)
    source_document_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = FindingEvidence
        fields = [
            "id", "source_document_id", "filename", "page_number",
            "rank", "score", "snippet", "is_validated",
        ]


class FindingSerializer(serializers.ModelSerializer):
    evidence = FindingEvidenceSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    status_description = serializers.SerializerMethodField()
    review_state_label = serializers.CharField(source="get_review_state_display", read_only=True)
    target_passage = serializers.SerializerMethodField()

    class Meta:
        model = Finding
        fields = [
            "id", "analysis_job_id", "status", "status_label", "status_description",
            "claim_text", "explanation", "confidence", "needs_human_review",
            "model_name", "model_version", "review_state", "review_state_label",
            "review_note", "target_passage", "evidence", "created_at",
        ]

    def get_status_description(self, obj):
        return FINDING_STATUS_DESCRIPTIONS.get(obj.status, "")

    def get_target_passage(self, obj):
        p = obj.target_passage
        return {
            "id": str(p.id),
            "document_id": str(p.document_id),
            "filename": p.document.original_filename,
            "page_number": p.page_number,
            "chunk_index": p.chunk_index,
            "text": p.text,
        }


class FindingReviewSerializer(serializers.Serializer):
    review_state = serializers.ChoiceField(choices=ReviewState.choices)
    review_note = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class WritingSuggestionSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    passage_ref = serializers.SerializerMethodField()

    class Meta:
        model = WritingSuggestion
        fields = ["id", "category", "category_label", "severity", "message", "suggestion", "passage_ref"]

    def get_passage_ref(self, obj):
        if not obj.target_passage_id:
            return None
        p = obj.target_passage
        return {"page_number": p.page_number, "chunk_index": p.chunk_index}


class FindingFilterSerializer(serializers.Serializer):
    status = serializers.CharField(required=False)
    review_state = serializers.CharField(required=False)
    min_confidence = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    needs_human_review = serializers.BooleanField(required=False)
