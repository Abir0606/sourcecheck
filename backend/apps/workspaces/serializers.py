from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Membership, Workspace

User = get_user_model()


class MembershipSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ["id", "user", "role", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_user(self, obj):
        return {
            "id": str(obj.user_id),
            "email": obj.user.email,
            "display_name": obj.user.display_name,
        }


class WorkspaceSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "id", "name", "slug", "data_region", "retention_days",
            "is_archived", "role", "member_count", "created_at",
        ]
        read_only_fields = ["id", "slug", "is_archived", "created_at"]

    def get_role(self, obj):
        request = self.context.get("request")
        return obj.role_for(request.user) if request else None

    def get_member_count(self, obj):
        return obj.memberships.count()

    def create(self, validated_data):
        request = self.context["request"]
        with transaction.atomic():
            workspace = Workspace.objects.create(created_by=request.user, **validated_data)
            Membership.objects.create(
                workspace=workspace, user=request.user, role="owner"
            )
        return workspace


class WorkspaceSettingsSerializer(serializers.ModelSerializer):
    """Only settings a workspace admin may change."""

    class Meta:
        model = Workspace
        fields = ["name", "data_region", "retention_days"]
