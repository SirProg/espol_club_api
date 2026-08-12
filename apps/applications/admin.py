from django.contrib import admin

from apps.applications.models import MembershipApplication


@admin.register(MembershipApplication)
class MembershipApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "club",
        "status",
        "created_at",
        "resolved_by",
        "resolved_at",
    )
    list_filter = ("status", "club")
    search_fields = (
        "student__enrollment",
        "student__first_name",
        "student__last_name",
        "club__acronym",
    )
    autocomplete_fields = ("student", "club")
    readonly_fields = (
        "form",
        "responses",
        "resulting_membership",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("student", "club", "form", "resolved_by")
        )

    def has_add_permission(self, request):
        # Las solicitudes las crea el estudiante desde la app. Darlas de alta a
        # mano dejaría respuestas sin validar contra el esquema.
        return False
