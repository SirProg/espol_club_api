"""
Vistas de autenticación y perfil.

Ninguna contiene lógica de negocio: validan la forma con un serializer, llaman
al servicio correspondiente y serializan la salida. Los errores no se capturan
aquí — el manejador global traduce los ``DomainError`` a su HTTP.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from api.v1.accounts.authentication import EspolclubTokenObtainPairSerializer
from api.v1.accounts.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    SessionSerializer,
    StudentProfileSerializer,
    VerifyEmailSerializer,
)
from apps.accounts.services import (
    confirm_password_reset,
    register_student,
    request_password_reset,
    resend_verification,
    update_profile,
    verify_email,
)


class RegisterView(APIView):
    """``POST /api/v1/auth/register/`` — RF-01, RF-05."""

    permission_classes = [AllowAny]
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student = register_student(**serializer.service_kwargs())
        return Response(
            {
                "profile": StudentProfileSerializer(student).data,
                "message": (
                    "Cuenta creada. Revisa tu correo institucional para "
                    "verificarla antes de iniciar sesión."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    """``POST /api/v1/auth/verify/`` — confirma la cuenta y dispara RF-12."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student = verify_email(token=serializer.validated_data["token"])
        return Response(
            {
                "profile": StudentProfileSerializer(student).data,
                "message": "Cuenta verificada. Ya puedes iniciar sesión.",
            }
        )


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resend_verification(email=serializer.validated_data["email"])
        # Respuesta idéntica exista o no la cuenta: si variara, el endpoint
        # serviría para averiguar qué correos están registrados.
        return Response(
            {
                "message": (
                    "Si ese correo tiene una cuenta pendiente de verificar, "
                    "acabamos de enviarle el enlace."
                )
            }
        )


class LoginView(TokenObtainPairView):
    """``POST /api/v1/auth/login/`` — RF-02. Acepta matrícula o correo."""

    permission_classes = [AllowAny]
    serializer_class = EspolclubTokenObtainPairSerializer
    throttle_scope = "auth_login"


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class PasswordResetRequestView(APIView):
    """``POST /api/v1/auth/password-reset/`` — RF-03."""

    permission_classes = [AllowAny]
    throttle_scope = "auth_password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request_password_reset(email=serializer.validated_data["email"])
        return Response(
            {
                "message": (
                    "Si ese correo tiene una cuenta, acabamos de enviarle las "
                    "instrucciones para restablecer la contraseña."
                )
            }
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth_password_reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        confirm_password_reset(
            uid=serializer.validated_data["uid"],
            token=serializer.validated_data["token"],
            password=serializer.validated_data["password"],
        )
        return Response({"message": "Contraseña actualizada. Ya puedes iniciar sesión."})


class SessionView(APIView):
    """
    ``GET /api/v1/auth/me/`` — contexto de sesión con el rol **derivado**.

    El rol no sale del token sino del estado actual de las membresías: un token
    emitido antes de una revocación de liderazgo no puede seguir afirmando que
    su portador es líder.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(SessionSerializer(request.user).data)


class ProfileView(APIView):
    """``GET/PATCH /api/v1/students/me/`` — RF-50, F-07."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(StudentProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        student = update_profile(student=request.user, **serializer.validated_data)
        return Response(StudentProfileSerializer(student).data)
