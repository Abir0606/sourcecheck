from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from apps.common.health import healthz, readyz


def index(_request):
    return JsonResponse({"service": "sourcecheck-api", "status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.common.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.workspaces.urls")),
    path("api/v1/", include("apps.documents.urls")),
    path("api/v1/", include("apps.analysis.urls")),
    path("api/v1/", include("apps.privacy.urls")),
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("", index),
]
