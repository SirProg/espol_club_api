"""
Comandos de cuentas (CU-AC1..AC6).

Las vistas de la API no contienen nada de esto: reciben datos validados, llaman
un servicio y serializan el resultado. Así el registro funciona igual desde la
API, desde el admin o desde un management command.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from apps.accounts.tokens import (
    build_password_reset_pair,
    build_verification_token,
    read_password_reset_pair,
    read_verification_token,
)
from core.events import emit
from core.exceptions import BusinessRuleViolation
from core.services import CLEAN_WITHOUT_UNIQUENESS, command

Student = get_user_model()


@command
def register_student(
    *,
    enrollment,
    first_name,
    last_name,
    email,
    password,
    birth_date=None,
    faculty=None,
    career="",
    semester=None,
):
    """
    CU-AC1 — alta de cuenta por el propio estudiante (RF-01, RF-05).

    La cuenta nace **sin verificar**: hasta seguir el enlace no puede iniciar
    sesión. ``is_gbp_admin`` no es parámetro y nunca lo será: el perfil
    institucional se provisiona aparte (PPD-02).
    """
    student = Student(
        enrollment=enrollment.strip().upper(),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email.strip().lower(),
        birth_date=birth_date,
        faculty=faculty,
        career=(career or "").strip(),
        semester=semester,
        is_verified=False,
    )
    student.full_clean(exclude=["password"], **CLEAN_WITHOUT_UNIQUENESS)
    student.set_password(password)
    student.save()

    send_verification_email(student)
    emit("student.registered", student=student)
    return student


def send_verification_email(student):
    """
    Envía el enlace de verificación.

    Se llama **fuera** de la transacción que crea la cuenta —vía el commit del
    comando— para no sostener una conexión SMTP con la transacción abierta.
    """
    token = build_verification_token(student)
    url = f"{settings.FRONTEND_BASE_URL}/verificacion.html?token={token}"

    send_mail(
        subject="Verifica tu cuenta de ESPOLCLUB",
        message=(
            f"Hola {student.first_name}:\n\n"
            f"Confirma tu cuenta institucional abriendo este enlace:\n\n{url}\n\n"
            f"El enlace caduca en 48 horas.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[student.email],
        fail_silently=False,
    )
    return token


@command
def verify_email(*, token):
    """
    CU-AC2 — confirmación de la cuenta (RF-01).

    Al verificarse se emite ``student.verified``, que es lo que dispara la
    activación diferida del liderazgo (RF-12) sin que este módulo conozca la app
    de clubes.
    """
    student = read_verification_token(token)
    if student is None:
        raise BusinessRuleViolation(
            "El enlace de verificación no es válido o ya caducó.",
            code="invalid_verification_token",
        )

    if student.is_verified:
        # Reabrir el enlace no es un error: el resultado deseado ya se cumplió.
        return student

    student.is_verified = True
    student.save(update_fields=["is_verified", "updated_at"])

    emit("student.verified", student=student)
    return student


@command
def resend_verification(*, email):
    """
    Reenvía el enlace de verificación.

    Responde igual exista o no la cuenta: decir "ese correo no está registrado"
    convertiría el endpoint en un comprobador de qué matrículas tienen cuenta.
    """
    student = Student.objects.filter(email=email.strip().lower()).first()
    if student and not student.is_verified:
        send_verification_email(student)
    return None


@command
def update_profile(*, student, description=None, skills=None, social_media=None):
    """
    CU-AC6 — edición del perfil propio (F-07).

    Solo estos tres campos son editables por el estudiante. Matrícula, correo,
    facultad y carrera son datos institucionales y no se tocan desde aquí.
    """
    if description is not None:
        student.description = description
    if skills is not None:
        student.skills = skills
    if social_media is not None:
        student.social_media = social_media

    student.full_clean(exclude=["password"], **CLEAN_WITHOUT_UNIQUENESS)
    student.save(
        update_fields=["description", "skills", "social_media", "updated_at"]
    )
    return student


@command
def request_password_reset(*, email):
    """
    CU-AC4 — solicitud de recuperación (RF-03).

    Igual que el reenvío de verificación: no revela si el correo existe.
    """
    student = Student.objects.filter(email=email.strip().lower()).first()
    if student is None:
        return None

    uid, token = build_password_reset_pair(student)
    url = f"{settings.FRONTEND_BASE_URL}/recuperacion.html?uid={uid}&token={token}"

    send_mail(
        subject="Restablece tu contraseña de ESPOLCLUB",
        message=(
            f"Hola {student.first_name}:\n\n"
            f"Para elegir una contraseña nueva, abre este enlace:\n\n{url}\n\n"
            f"Si no lo solicitaste, ignora este mensaje.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[student.email],
        fail_silently=False,
    )
    return None


@command
def confirm_password_reset(*, uid, token, password):
    """CU-AC4 — fijación de la contraseña nueva."""
    student = read_password_reset_pair(uid, token)
    if student is None:
        raise BusinessRuleViolation(
            "El enlace de recuperación no es válido o ya fue utilizado.",
            code="invalid_reset_token",
        )

    student.set_password(password)
    # Cambiar la contraseña invalida el propio token, porque el generador de
    # Django lo deriva del hash actual: el enlace no sirve dos veces.
    student.save(update_fields=["password", "updated_at"])
    return student
