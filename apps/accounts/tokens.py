"""
Tokens firmados para verificación de correo y recuperación de contraseña.

Se usa ``django.core.signing`` en vez de guardar tokens en una tabla: el enlace
lleva su propia validez firmada y caduca solo, sin dejar filas huérfanas que
limpiar. El mismo mecanismo respalda el ``qr_token`` de la Etapa 7.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import signing
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

Student = get_user_model()

password_reset_token_generator = PasswordResetTokenGenerator()


def build_verification_token(student):
    """Token de verificación de correo, con caducidad propia (RF-01)."""
    return signing.dumps(
        {"pk": student.pk, "email": student.email},
        salt=settings.EMAIL_VERIFICATION_SALT,
    )


def read_verification_token(token):
    """
    Devuelve el estudiante del token, o ``None`` si no sirve.

    Comprueba también que el correo firmado siga siendo el de la cuenta: así un
    enlace emitido antes de un cambio de correo deja de valer.
    """
    try:
        payload = signing.loads(
            token,
            salt=settings.EMAIL_VERIFICATION_SALT,
            max_age=settings.EMAIL_VERIFICATION_MAX_AGE,
        )
    except signing.BadSignature:
        return None

    student = Student.objects.filter(pk=payload.get("pk")).first()
    if student is None or student.email != payload.get("email"):
        return None
    return student


def build_password_reset_pair(student):
    """Par (uid, token) para el enlace de recuperación (RF-03)."""
    return (
        urlsafe_base64_encode(force_bytes(student.pk)),
        password_reset_token_generator.make_token(student),
    )


def read_password_reset_pair(uid, token):
    """
    Devuelve el estudiante si el par es válido.

    El token de Django incorpora el hash de la contraseña actual, así que se
    invalida solo en cuanto la contraseña cambia: un enlace no sirve dos veces.
    """
    try:
        pk = force_str(urlsafe_base64_decode(uid))
    except (TypeError, ValueError, OverflowError):
        return None

    student = Student.objects.filter(pk=pk).first()
    if student is None:
        return None
    if not password_reset_token_generator.check_token(student, token):
        return None
    return student
