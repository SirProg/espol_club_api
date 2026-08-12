"""
Serializers de cuentas.

Su trabajo es la **forma** de los datos: tipos, obligatoriedad, coherencia entre
campos del propio payload. Las reglas de negocio viven en los servicios; aquí no
se decide nada que dependa del estado de la base más allá de la unicidad, que se
comprueba para dar un error atribuido al campo.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import AppRole
from apps.catalogs.models import Faculty
from core.validators import validate_espol_email

Student = get_user_model()


class PasswordPairMixin(serializers.Serializer):
    """Contraseña repetida, validada con las reglas de Django."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        return attrs


class RegisterSerializer(PasswordPairMixin, serializers.Serializer):
    """F-02 — formulario de registro (RF-01, RF-05)."""

    enrollment = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    email = serializers.EmailField(validators=[validate_espol_email])
    birth_date = serializers.DateField(required=False, allow_null=True)
    faculty = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Faculty.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    career = serializers.CharField(max_length=120, required=False, allow_blank=True)
    semester = serializers.IntegerField(min_value=1, max_value=20, required=False)

    def validate_enrollment(self, value):
        value = value.strip().upper()
        if Student.objects.filter(enrollment=value).exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta registrada con esa matrícula."
            )
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if Student.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta registrada con ese correo."
            )
        return value

    def service_kwargs(self):
        """
        Argumentos para ``register_student``.

        Se construye explícitamente en vez de volcar ``validated_data``: así un
        campo nuevo del formulario no llega al servicio por accidente, que es
        como ``is_gbp_admin`` acabaría siendo asignable desde el registro.
        """
        data = self.validated_data
        return {
            "enrollment": data["enrollment"],
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "email": data["email"],
            "password": data["password"],
            "birth_date": data.get("birth_date"),
            "faculty": data.get("faculty"),
            "career": data.get("career", ""),
            "semester": data.get("semester"),
        }


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(PasswordPairMixin, serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()


class ProfileUpdateSerializer(serializers.Serializer):
    """
    F-07 — lo único que el estudiante edita de sí mismo.

    Matrícula, correo, facultad y carrera son datos institucionales: si
    estuvieran aquí, cualquiera podría cambiarse de facultad desde la app.
    """

    description = serializers.CharField(required=False, allow_blank=True)
    skills = serializers.ListField(
        child=serializers.CharField(max_length=60), required=False
    )
    social_media = serializers.ListField(child=serializers.DictField(), required=False)


class FacultyBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ["id", "code", "name"]


class StudentProfileSerializer(serializers.ModelSerializer):
    """Perfil propio: el estudiante sí ve todos sus datos (RF-50)."""

    faculty = FacultyBriefSerializer(read_only=True)
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = Student
        fields = [
            "id",
            "enrollment",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "birth_date",
            "age",
            "faculty",
            "career",
            "semester",
            "description",
            "skills",
            "social_media",
            "is_verified",
        ]
        read_only_fields = fields


class MembershipContextSerializer(serializers.Serializer):
    """
    Membresía tal como la necesita el cliente para decidir qué mostrar.

    Incluye los permisos ya resueltos: así el frontend no tiene que replicar la
    lógica de roles para saber si pinta el botón de 'Gestionar miembros'. La
    autorización real sigue estando en el servidor — esto solo evita ofrecer
    acciones que después serían rechazadas.
    """

    club_id = serializers.IntegerField(source="club.id")
    club_name = serializers.CharField(source="club.name")
    club_acronym = serializers.CharField(source="club.acronym")
    club_status = serializers.CharField(source="club.status")
    role_id = serializers.IntegerField(source="role.id")
    role_name = serializers.CharField(source="role.role_name")
    is_leadership = serializers.BooleanField()
    permissions = serializers.SerializerMethodField()

    def get_permissions(self, membership):
        return membership.role.granted_permissions


class SessionSerializer(serializers.Serializer):
    """
    Respuesta de ``/auth/me/`` — el contexto de sesión completo.

    Reemplaza al objeto que la Fase 1 guardaba en ``localStorage``
    (``{enrollment, role, club_id, role_id, ...}``), pero con el rol **derivado
    en el servidor** en vez de fijado al iniciar sesión: si a alguien le revocan
    el liderazgo, su siguiente petición ya lo refleja.
    """

    profile = StudentProfileSerializer(read_only=True)
    app_role = serializers.SerializerMethodField()
    app_role_label = serializers.SerializerMethodField()
    is_gbp_admin = serializers.BooleanField()
    led_club_id = serializers.SerializerMethodField()
    memberships = serializers.SerializerMethodField()

    def get_app_role(self, student):
        return student.app_role.value

    def get_app_role_label(self, student):
        return student.app_role.label

    def get_led_club_id(self, student):
        from apps.clubs.selectors import get_led_club

        club = get_led_club(student)
        return club.pk if club else None

    def get_memberships(self, student):
        from apps.clubs.selectors import get_active_memberships

        return MembershipContextSerializer(
            get_active_memberships(student), many=True
        ).data

    def to_representation(self, instance):
        # El serializer recibe el propio estudiante, así que 'profile' apunta a
        # la misma instancia.
        data = super().to_representation(instance)
        data["profile"] = StudentProfileSerializer(instance).data
        return data


__all__ = [
    "RegisterSerializer",
    "VerifyEmailSerializer",
    "ResendVerificationSerializer",
    "PasswordResetRequestSerializer",
    "PasswordResetConfirmSerializer",
    "ProfileUpdateSerializer",
    "StudentProfileSerializer",
    "SessionSerializer",
    "AppRole",
]
