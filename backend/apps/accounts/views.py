from __future__ import annotations

from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.audit import record_audit_event

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


def _session_payload(request) -> dict:
    return {
        "authenticated": request.user.is_authenticated,
        "user": UserSerializer(request.user).data if request.user.is_authenticated else None,
        "csrfToken": get_token(request),
    }


class SessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(_session_payload(request))


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "anon"

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        record_audit_event(action="auth.login", actor=user, request=request)
        return Response(_session_payload(request))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        record_audit_event(action="auth.logout", actor=request.user, request=request)
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "anon"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        record_audit_event(action="auth.register", actor=user, request=request)
        return Response(_session_payload(request), status=status.HTTP_201_CREATED)
