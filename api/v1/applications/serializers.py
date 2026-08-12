"""Serializers de solicitudes de membresía."""

from rest_framework import serializers

from apps.applications.models import MembershipApplication


class ApplicantSerializer(serializers.Serializer):
    """
    Datos del postulante que el líder necesita para decidir.

    Incluye matrícula y correo porque quien lee esto tiene ``manage_members``:
    es la vista interna del club, no la pública (RN-3).
    """

    id = serializers.IntegerField()
    enrollment = serializers.CharField()
    full_name = serializers.CharField(source="get_full_name")
    email = serializers.EmailField()
    faculty = serializers.CharField(source="faculty.code", default=None)
    career = serializers.CharField()
    semester = serializers.IntegerField()


class ApplicationSerializer(serializers.ModelSerializer):
    """
    Solicitud tal como la ve la bandeja del líder (V-15).

    Las respuestas vienen ya emparejadas con su pregunta: sin eso el panel
    tendría que pedir el formulario aparte y reconstruir el emparejamiento, y
    haría falta acertar con la **versión** correcta del esquema.
    """

    student = ApplicantSerializer(read_only=True)
    club_acronym = serializers.CharField(source="club.acronym", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    submitted_at = serializers.DateTimeField(read_only=True)
    answers = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MembershipApplication
        fields = [
            "id",
            "student",
            "club",
            "club_acronym",
            "form",
            "status",
            "status_label",
            "submitted_at",
            "answers",
            "leader_feedback",
            "resolved_by_name",
            "resolved_at",
            "resulting_membership",
        ]
        read_only_fields = fields

    def get_answers(self, application):
        return application.answers_with_labels()

    def get_resolved_by_name(self, application):
        return (
            application.resolved_by.get_full_name()
            if application.resolved_by_id
            else None
        )


class StudentApplicationSerializer(serializers.ModelSerializer):
    """
    La misma solicitud, vista por su autor (RF-50).

    No incluye sus propios datos personales —ya los conoce— ni quién la
    resolvió: para el estudiante la decisión es del club, no de una persona
    concreta, y exponer el nombre invitaría a reclamaciones individuales.
    """

    club_name = serializers.CharField(source="club.name", read_only=True)
    club_acronym = serializers.CharField(source="club.acronym", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    submitted_at = serializers.DateTimeField(read_only=True)
    answers = serializers.SerializerMethodField()

    class Meta:
        model = MembershipApplication
        fields = [
            "id",
            "club",
            "club_name",
            "club_acronym",
            "status",
            "status_label",
            "submitted_at",
            "answers",
            "leader_feedback",
            "resolved_at",
        ]
        read_only_fields = fields

    def get_answers(self, application):
        return application.answers_with_labels()


class SubmitApplicationSerializer(serializers.Serializer):
    """F-05 — el envío del formulario dinámico."""

    responses = serializers.JSONField()


class RejectApplicationSerializer(serializers.Serializer):
    """RN-5 — el feedback es obligatorio y no puede ser espacios en blanco."""

    feedback = serializers.CharField(allow_blank=False, trim_whitespace=True)

    def validate_feedback(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Debes explicar el motivo del rechazo (RN-5)."
            )
        return value.strip()


class CanApplySerializer(serializers.Serializer):
    """Respuesta de la comprobación previa, con el mensaje canónico de MASTER §12."""

    allowed = serializers.BooleanField()
    reason = serializers.CharField(allow_null=True)
    code = serializers.CharField(allow_null=True)
