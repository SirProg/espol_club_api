"""Serializers de eventos, inscripciones y asistencia."""

from rest_framework import serializers

from apps.events.models import Event, EventRegistration, EventStaff


class EventListSerializer(serializers.ModelSerializer):
    """
    Tarjeta de evento del catálogo móvil (V-04).

    Incluye la etiqueta de ``MembersOnly`` porque el evento **se muestra** aunque
    el estudiante no pueda inscribirse (RF-31): la etiqueta es lo que explica
    por qué el botón está bloqueado.
    """

    club_acronym = serializers.CharField(source="club.acronym", read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True)
    mode_label = serializers.CharField(source="get_mode_display", read_only=True)
    visibility_label = serializers.CharField(
        source="get_visibility_display", read_only=True
    )
    registration_is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "club",
            "club_acronym",
            "club_name",
            "event_name",
            "mode",
            "mode_label",
            "planned_date",
            "planned_hour",
            "start_datetime",
            "end_datetime",
            "planned_place",
            "marketing_image",
            "visibility",
            "visibility_label",
            "registration_is_open",
        ]
        read_only_fields = fields


class EventDetailSerializer(EventListSerializer):
    """Detalle del evento, con el veredicto de registro ya resuelto (V-05)."""

    can_register = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + [
            "description",
            "registration_form",
            "registration_deadline",
            "blocked_message",
            "expected_participants",
            "can_register",
            "stats",
        ]
        read_only_fields = fields

    def get_can_register(self, event):
        """
        El veredicto viaja con el detalle para que la app no tenga que pedirlo
        aparte solo para decidir si habilita el botón.
        """
        from apps.events.services.events import can_register

        student = self.context["request"].user
        return can_register(student, event)

    def get_stats(self, event):
        # En listados vienen anotados; en el detalle se calculan.
        registered = getattr(event, "registered_count", None)
        attended = getattr(event, "attended_count", None)
        if registered is None or attended is None:
            return event.stats
        return {"registered": registered, "attended": attended}


class EventManagementSerializer(EventDetailSerializer):
    """
    Vista del líder: añade las métricas de desempeño (V-17).

    Es la misma entidad con dos proyecciones, igual que el club público frente
    al interno: quien gestiona ve cifras que al estudiante no le corresponden.
    """

    class Meta(EventDetailSerializer.Meta):
        fields = EventDetailSerializer.Meta.fields
        read_only_fields = fields


class EventWriteSerializer(serializers.Serializer):
    """F-13 — creación y edición de un evento."""

    event_name = serializers.CharField(max_length=150)
    mode = serializers.ChoiceField(choices=Event.Mode.choices)
    planned_date = serializers.DateField()
    planned_hour = serializers.TimeField()
    end_datetime = serializers.DateTimeField()
    planned_place = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    marketing_image = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    visibility = serializers.ChoiceField(
        choices=Event.Visibility.choices, default=Event.Visibility.PUBLIC
    )
    registration_form_id = serializers.IntegerField(required=False, allow_null=True)
    registration_deadline = serializers.DateTimeField(required=False, allow_null=True)
    blocked_message = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    expected_participants = serializers.IntegerField(
        required=False, allow_null=True, min_value=0
    )


class EventStaffMemberSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    enrollment = serializers.CharField(source="student.enrollment", read_only=True)
    full_name = serializers.CharField(source="student.get_full_name", read_only=True)

    class Meta:
        model = EventStaff
        fields = ["id", "student_id", "enrollment", "full_name", "created_at"]
        read_only_fields = fields


class SetEventStaffSerializer(serializers.Serializer):
    """F-14 — reemplaza la asignación completa."""

    student_ids = serializers.ListField(child=serializers.IntegerField())


class RegisterForEventSerializer(serializers.Serializer):
    """F-06 — envío del formulario dinámico de inscripción."""

    responses = serializers.JSONField()


class CredentialSerializer(serializers.ModelSerializer):
    """
    Credencial QR del estudiante (pantalla 12).

    El token va aquí porque es lo que la app convierte en código de barras. Solo
    se expone al dueño de la inscripción.
    """

    event_name = serializers.CharField(source="event.event_name", read_only=True)
    club_acronym = serializers.CharField(source="event.club.acronym", read_only=True)
    starts_at = serializers.DateTimeField(source="event.start_datetime", read_only=True)
    place = serializers.CharField(source="event.planned_place", read_only=True)
    qr_status_label = serializers.CharField(
        source="get_qr_status_display", read_only=True
    )
    attendance_status_label = serializers.CharField(
        source="get_attendance_status_display", read_only=True
    )

    class Meta:
        model = EventRegistration
        fields = [
            "id",
            "event",
            "event_name",
            "club_acronym",
            "starts_at",
            "place",
            "qr_token",
            "qr_status",
            "qr_status_label",
            "attendance_status",
            "attendance_status_label",
            "created_at",
        ]
        read_only_fields = fields


class RegistrationLogSerializer(serializers.ModelSerializer):
    """
    Bitácora de inscritos de un evento (pantalla 34, resuelve PPD-04).

    La lee la directiva del club, así que incluye matrícula: es la vista
    interna, no la pública.
    """

    student_id = serializers.IntegerField(source="student.id", read_only=True)
    enrollment = serializers.CharField(source="student.enrollment", read_only=True)
    full_name = serializers.CharField(source="student.get_full_name", read_only=True)
    faculty = serializers.CharField(source="student.faculty.code", default=None)
    attendance_status_label = serializers.CharField(
        source="get_attendance_status_display", read_only=True
    )
    registered_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = EventRegistration
        fields = [
            "id",
            "student_id",
            "enrollment",
            "full_name",
            "faculty",
            "registered_at",
            "attendance_status",
            "attendance_status_label",
            "qr_status",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Las respuestas del formulario van aparte y solo si se piden: la
        # bitácora se usa para pasar lista, no para leer formularios.
        if self.context.get("include_responses"):
            data["responses"] = instance.responses
        return data


class ScanSerializer(serializers.Serializer):
    """Lo único que envía el escáner: el token leído del código."""

    qr_token = serializers.CharField(allow_blank=True, trim_whitespace=True)
