from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MembershipViewSet, WorkspaceViewSet

router = DefaultRouter()
router.register("workspaces", WorkspaceViewSet, basename="workspace")

members_list = MembershipViewSet.as_view({"get": "list", "post": "create"})
members_detail = MembershipViewSet.as_view({"delete": "destroy"})

urlpatterns = router.urls + [
    path("workspaces/<uuid:workspace_pk>/members", members_list, name="workspace-members"),
    path("workspaces/<uuid:workspace_pk>/members/<uuid:pk>", members_detail, name="workspace-member-detail"),
]
