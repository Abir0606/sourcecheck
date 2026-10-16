from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .constants import (
    FINDING_STATUS_DESCRIPTIONS,
    AnalysisStatus,
    DocumentRole,
    DocumentStatus,
    FindingStatus,
    ReviewState,
    WorkspaceRole,
    WritingCategory,
)


class EnumsView(APIView):
    """
    Exposes shared vocabulary + label descriptions so the UI never invents
    wording (particularly the "not found in uploaded sources" nuance).
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        def choices(enum):
            return [{"value": v, "label": label} for v, label in enum.choices]

        return Response(
            {
                "finding_status": choices(FindingStatus),
                "finding_status_descriptions": FINDING_STATUS_DESCRIPTIONS,
                "document_role": choices(DocumentRole),
                "document_status": choices(DocumentStatus),
                "workspace_role": choices(WorkspaceRole),
                "analysis_status": choices(AnalysisStatus),
                "review_state": choices(ReviewState),
                "writing_category": choices(WritingCategory),
            }
        )
