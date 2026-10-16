from django.urls import path

from .views import AnalysisJobViewSet, FindingViewSet

analyses_list = AnalysisJobViewSet.as_view({"get": "list", "post": "create"})
analysis_detail = AnalysisJobViewSet.as_view({"get": "retrieve"})
analysis_status = AnalysisJobViewSet.as_view({"get": "status"})
analysis_cancel = AnalysisJobViewSet.as_view({"post": "cancel"})
analysis_retry = AnalysisJobViewSet.as_view({"post": "retry"})
analysis_findings = AnalysisJobViewSet.as_view({"get": "findings"})
analysis_writing = AnalysisJobViewSet.as_view({"get": "writing"})
analysis_report = AnalysisJobViewSet.as_view({"get": "report"})

finding_detail = FindingViewSet.as_view({"get": "retrieve", "patch": "partial_update"})

urlpatterns = [
    path("workspaces/<uuid:workspace_pk>/analyses", analyses_list, name="analysis-list"),
    path("workspaces/<uuid:workspace_pk>/analyses/<uuid:pk>", analysis_detail, name="analysis-detail"),
    path("workspaces/<uuid:workspace_pk>/analyses/<uuid:pk>/status", analysis_status, name="analysis-status"),
    path("workspaces/<uuid:workspace_pk>/analyses/<uuid:pk>/cancel", analysis_cancel, name="analysis-cancel"),
    path("workspaces/<uuid:workspace_pk>/analyses/<uuid:pk>/retry", analysis_retry, name="analysis-retry"),
    path("workspaces/<uuid:workspace_pk>/analyses/<uuid:pk>/findings", analysis_findings, name="analysis-findings"),
    path("workspaces/<uuid:workspace_pk>/analyses/<uuid:pk>/writing", analysis_writing, name="analysis-writing"),
    path("workspaces/<uuid:workspace_pk>/analyses/<uuid:pk>/report", analysis_report, name="analysis-report"),
    path("workspaces/<uuid:workspace_pk>/findings/<uuid:pk>", finding_detail, name="finding-detail"),
]
