from django.urls import path

from . import views

app_name = "common"

urlpatterns = [
    path("meta/enums", views.EnumsView.as_view(), name="enums"),
]
