from django.urls import path

from .views import DocumentViewSet

documents_list = DocumentViewSet.as_view({"get": "list", "post": "create"})
document_detail = DocumentViewSet.as_view({"get": "retrieve", "delete": "destroy"})
document_status = DocumentViewSet.as_view({"get": "status"})
document_reprocess = DocumentViewSet.as_view({"post": "reprocess"})
document_passages = DocumentViewSet.as_view({"get": "passages"})

urlpatterns = [
    path("workspaces/<uuid:workspace_pk>/documents", documents_list, name="document-list"),
    path("workspaces/<uuid:workspace_pk>/documents/<uuid:pk>", document_detail, name="document-detail"),
    path("workspaces/<uuid:workspace_pk>/documents/<uuid:pk>/status", document_status, name="document-status"),
    path("workspaces/<uuid:workspace_pk>/documents/<uuid:pk>/reprocess", document_reprocess, name="document-reprocess"),
    path("workspaces/<uuid:workspace_pk>/documents/<uuid:pk>/passages", document_passages, name="document-passages"),
]
