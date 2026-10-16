from django.urls import path

from .views import DeletionRequestViewSet, ExportViewSet, PrivacyOverviewView

exports_list = ExportViewSet.as_view({"get": "list", "post": "create"})
export_detail = ExportViewSet.as_view({"get": "retrieve"})
export_download = ExportViewSet.as_view({"get": "download"})

deletions_list = DeletionRequestViewSet.as_view({"get": "list", "post": "create"})
deletion_detail = DeletionRequestViewSet.as_view({"get": "retrieve"})

urlpatterns = [
    path("workspaces/<uuid:workspace_pk>/privacy", PrivacyOverviewView.as_view(), name="privacy-overview"),
    path("workspaces/<uuid:workspace_pk>/exports", exports_list, name="export-list"),
    path("workspaces/<uuid:workspace_pk>/exports/<uuid:pk>", export_detail, name="export-detail"),
    path("workspaces/<uuid:workspace_pk>/exports/<uuid:pk>/download", export_download, name="export-download"),
    path("workspaces/<uuid:workspace_pk>/deletion-requests", deletions_list, name="deletion-list"),
    path("workspaces/<uuid:workspace_pk>/deletion-requests/<uuid:pk>", deletion_detail, name="deletion-detail"),
]
