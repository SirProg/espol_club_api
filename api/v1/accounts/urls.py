"""Rutas de autenticación y perfil (MASTER §16.6)."""

from django.urls import path

from api.v1.accounts.views import (
    LoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ProfileView,
    RefreshView,
    RegisterView,
    ResendVerificationView,
    SessionView,
    VerifyEmailView,
)

app_name = "accounts"

auth_urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify/", VerifyEmailView.as_view(), name="verify"),
    path("verify/resend/", ResendVerificationView.as_view(), name="verify-resend"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path(
        "password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("me/", SessionView.as_view(), name="session"),
]

student_urlpatterns = [
    path("me/", ProfileView.as_view(), name="profile"),
]
