"""
Emisión de tokens JWT (RF-02, RNF-04).

Dos desviaciones del comportamiento por defecto de ``simplejwt``, ambas
exigidas por el negocio:

1. El identificador puede ser la **matrícula o el correo**. MASTER §16.4 lo pide
   explícitamente, y tiene sentido: la matrícula es la clave institucional, pero
   el correo es lo que el estudiante recuerda.
2. Una cuenta **sin verificar no inicia sesión** (RF-01). El error lleva un
   código propio para que el cliente pueda ofrecer "reenviar el enlace" en vez
   de un mensaje genérico de credenciales inválidas.
"""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings

from core.exceptions import DomainError

Student = get_user_model()


class AccountNotVerified(DomainError):
    code = "account_not_verified"
    default_message = (
        "Tu cuenta aún no está verificada. Revisa el enlace que enviamos a tu "
        "correo institucional."
    )
    http_status = 403


class EspolclubTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login por matrícula o correo, con el contexto de sesión en la respuesta."""

    username_field = "identifier"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La clase base declara el campo con el nombre de USERNAME_FIELD
        # ('enrollment'); aquí el campo es genérico porque acepta las dos cosas.
        self.fields.pop(Student.USERNAME_FIELD, None)
        self.fields["identifier"] = serializers.CharField()

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Claims de conveniencia para el cliente. NO son autoridad: el servidor
        # vuelve a derivar el rol en cada petición, porque un token emitido
        # antes de una revocación seguiría afirmando lo viejo.
        token["enrollment"] = user.enrollment
        token["app_role"] = user.app_role.value
        return token

    def validate(self, attrs):
        identifier = (attrs.get("identifier") or "").strip()
        password = attrs.get("password") or ""

        student = self._resolve_student(identifier)
        if student is None:
            # 401 y no 400: el problema no es la forma del payload sino la
            # autenticación. Y el mensaje es idéntico tanto si la cuenta no
            # existe como si la contraseña falla, para no revelar qué
            # matrículas están registradas.
            raise AuthenticationFailed(
                "La matrícula o el correo no corresponden a ninguna cuenta, o la "
                "contraseña es incorrecta.",
                code="invalid_credentials",
            )

        user = authenticate(
            request=self.context.get("request"),
            **{Student.USERNAME_FIELD: student.enrollment},
            password=password,
        )
        if user is None:
            # 401 y no 400: el problema no es la forma del payload sino la
            # autenticación. Y el mensaje es idéntico tanto si la cuenta no
            # existe como si la contraseña falla, para no revelar qué
            # matrículas están registradas.
            raise AuthenticationFailed(
                "La matrícula o el correo no corresponden a ninguna cuenta, o la "
                "contraseña es incorrecta.",
                code="invalid_credentials",
            )
        if not user.is_verified:
            raise AccountNotVerified()

        refresh = self.get_token(user)
        self.user = user

        # Este validate no llama al de la superclase (resuelve el identificador
        # por su cuenta), así que el registro de last_login se hace aquí.
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, user)

        return {"access": str(refresh.access_token), "refresh": str(refresh)}

    @staticmethod
    def _resolve_student(identifier):
        """Un identificador con '@' es un correo; el resto, una matrícula."""
        if not identifier:
            return None
        if "@" in identifier:
            return Student.objects.filter(email=identifier.lower()).first()
        return Student.objects.filter(enrollment=identifier.upper()).first()
