from django.contrib import admin

from apps.events.models import (
    Event,
    EventAdministrativeData,
    EventAttendance,
    EventRegistration,
    EventStaff,
)


class EventStaffInline(admin.TabularInline):
    model = EventStaff
    extra = 0
    autocomplete_fields = ("student",)
    fields = ("student", "assigned_by")
    readonly_fields = ("assigned_by",)


class EventAdministrativeDataInline(admin.StackedInline):
    model = EventAdministrativeData
    extra = 0
    autocomplete_fields = ("responsible_member",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "event_name",
        "club",
        "start_datetime",
        "mode",
        "visibility",
        "registered",
        "attended",
    )
    list_filter = ("visibility", "mode", "club")
    search_fields = ("event_name", "club__acronym")
    readonly_fields = ("start_datetime", "created_at", "updated_at")
    inlines = [EventStaffInline, EventAdministrativeDataInline]

    def get_queryset(self, request):
        from apps.events.selectors import _with_stats

        return _with_stats(super().get_queryset(request).select_related("club"))

    @admin.display(description="inscritos")
    def registered(self, obj):
        return obj.registered_count

    @admin.display(description="asistentes")
    def attended(self, obj):
        return obj.attended_count


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "event",
        "qr_status",
        "attendance_status",
        "created_at",
    )
    list_filter = ("qr_status", "attendance_status", "event__club")
    search_fields = ("student__enrollment", "event__event_name")
    readonly_fields = ("qr_token", "responses", "created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("student", "event")

    def has_add_permission(self, request):
        # Las inscripciones nacen del flujo del estudiante, que emite el token
        # firmado. Crearlas a mano dejaría credenciales inválidas.
        return False


@admin.register(EventAttendance)
class EventAttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "event", "scanned_at", "scanned_by_staff")
    list_filter = ("event__club",)
    search_fields = ("student__enrollment", "event__event_name")
    readonly_fields = tuple(
        field.name for field in EventAttendance._meta.fields
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("student", "event", "scanned_by_staff")
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # RNF-12: los registros de asistencia son inmutables al momento del
        # escaneo. Son evidencia, no un dato administrativo.
        return False


@admin.register(EventStaff)
class EventStaffAdmin(admin.ModelAdmin):
    list_display = ("student", "event", "assigned_by")
    search_fields = ("student__enrollment", "event__event_name")
    autocomplete_fields = ("student",)
