from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("session", views.SessionView.as_view(), name="session"),
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("register", views.RegisterView.as_view(), name="register"),
]
