"""
Identidad del sistema.

``Student`` es el ``AUTH_USER_MODEL``: no hay un "usuario" separado del
estudiante. La matrícula es la clave natural institucional (MASTER §7.2) y el
identificador de inicio de sesión, porque es el dato que GBP usa para vincular
un líder a un club antes incluso de que esa persona tenga cuenta (RF-11/RF-12).
"""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel
from core.validators import (
    validate_espol_email,
    validate_not_future_date,
    validate_social_media,
    validate_string_list,
)


class AppRole(models.TextChoices):
    """
    Rol de aplicación (MASTER §2).

    **No se almacena**: se deriva del estado de las membresías (decisión D-11).
    Solo determina el "hogar" de navegación tras el login; los permisos
    operativos siempre se resuelven por club vía ``Membership.role.permissions``.
    """

    GBP_ADMIN = "GBP Admin", "Administrador GBP"
    CLUB_LEADER = "Club Leader", "Líder de Club"
    CLUB_MEMBER = "Club Member", "Miembro del Club"
    STUDENT = "Student", "Estudiante Politécnico"


class StudentManager(BaseUserManager):
    """Manager con la matrícula como identificador en vez de un username."""

    use_in_migrations = True

    def _create_user(self, enrollment, email, password, **extra_fields):
        if not enrollment:
            raise ValueError("La matrícula es obligatoria.")
        if not email:
            raise ValueError("El correo institucional es obligatorio.")

        user = self.model(
            enrollment=enrollment.strip().upper(),
            email=self.normalize_email(email).lower(),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, enrollment, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_verified", False)
        return self._create_user(enrollment, email, password, **extra_fields)

    def create_superuser(self, enrollment, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        # Un superusuario entra al admin sin pasar por el flujo de verificación
        # por correo, así que se marca verificado de entrada.
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Un superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Un superusuario debe tener is_superuser=True.")

        return self._create_user(enrollment, email, password, **extra_fields)


class Student(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Estudiante politécnico o personal de GBP.

    Las pertenencias a clubes **no** viven aquí: viven en ``Membership``, porque
    un estudiante puede pertenecer a varios clubes y cada pertenencia tiene su
    propio rol y vigencia por período (RF-17, RF-18).
    """

    enrollment = models.CharField(
        "matrícula",
        max_length=20,
        unique=True,
        help_text="Matrícula institucional (202311346) o código GBP (GBP-001).",
    )
    first_name = models.CharField("nombres", max_length=80)
    last_name = models.CharField("apellidos", max_length=80)
    email = models.EmailField(
        "correo institucional",
        unique=True,
        validators=[validate_espol_email],
    )
    birth_date = models.DateField(
        "fecha de nacimiento",
        null=True,
        blank=True,
        validators=[validate_not_future_date],
    )

    # Nulos para el personal GBP, que no pertenece a ninguna facultad ni carrera.
    semester = models.PositiveSmallIntegerField("semestre", null=True, blank=True)
    faculty = models.ForeignKey(
        "catalogs.Faculty",
        verbose_name="facultad",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="students",
    )
    career = models.CharField("carrera", max_length=120, blank=True)

    # Editables por el propio estudiante (F-07).
    description = models.TextField("descripción", blank=True)
    skills = models.JSONField(
        "habilidades", default=list, blank=True, validators=[validate_string_list]
    )
    social_media = models.JSONField(
        "redes sociales",
        default=list,
        blank=True,
        validators=[validate_social_media],
        help_text='Lista de objetos {"network": "GitHub", "link": "https://..."}.',
    )

    is_gbp_admin = models.BooleanField(
        "administrador GBP",
        default=False,
        help_text="Perfil institucional. Se provisiona manualmente (PPD-02); "
        "nunca por auto-registro.",
    )
    is_verified = models.BooleanField(
        "correo verificado",
        default=False,
        help_text="RF-01: se activa al seguir el enlace enviado por correo.",
    )
    is_active = models.BooleanField("cuenta habilitada", default=True)
    is_staff = models.BooleanField("acceso al admin de Django", default=False)

    objects = StudentManager()

    USERNAME_FIELD = "enrollment"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    class Meta:
        verbose_name = "estudiante"
        verbose_name_plural = "estudiantes"
        ordering = ["last_name", "first_name"]
        indexes = [
            # El catálogo y las pantallas de nómina buscan por apellido/nombre.
            models.Index(fields=["last_name", "first_name"], name="idx_student_name"),
        ]

    def __str__(self):
        return f"{self.enrollment} — {self.get_full_name()}"

    def clean(self):
        super().clean()
        if self.enrollment:
            self.enrollment = self.enrollment.strip().upper()
        if self.email:
            self.email = self.email.strip().lower()
        if self.birth_date:
            validate_not_future_date(self.birth_date)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    @property
    def age(self):
        """
        Edad derivada. MASTER §7.2 es explícito: la edad no se almacena.

        Guardarla sería garantizar que quede desactualizada.
        """
        if not self.birth_date:
            return None
        today = timezone.localdate()
        return (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )

    @property
    def app_role(self):
        """
        Rol de aplicación derivado, por precedencia (decisión D-12):
        GBP Admin > Líder de Club > Miembro del Club > Estudiante Politécnico.

        Solo determina el "hogar" de navegación tras el login. Los permisos
        operativos **no** salen de aquí: se resuelven siempre por club, vía
        ``Membership.role.permissions`` (ver ``clubs.policies``).

        GBP es excluyente: una cuenta institucional no participa en clubes.
        """
        if self.is_gbp_admin:
            return AppRole.GBP_ADMIN

        # Una instancia todavía sin guardar no puede tener membresías, y
        # consultarlas por una FK sin pk lanza ValueError. Los serializers
        # acceden a esta propiedad sobre instancias en construcción.
        if self.pk is None:
            return AppRole.STUDENT

        # Import local a propósito: 'clubs' depende de 'accounts', así que
        # importarlo a nivel de módulo cerraría un ciclo. La derivación conoce
        # a clubs, pero solo en tiempo de ejecución.
        from apps.clubs.models import Membership

        memberships = Membership.objects.filter(
            student=self, status=Membership.Status.ACTIVE
        )
        if memberships.filter(is_leadership=True).exists():
            return AppRole.CLUB_LEADER
        if memberships.exists():
            return AppRole.CLUB_MEMBER
        return AppRole.STUDENT
