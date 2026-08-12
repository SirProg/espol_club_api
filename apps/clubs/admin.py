from django.contrib import admin, messages

from apps.clubs.models import Club, ClubDocument, Membership, Role
from apps.clubs.services.leadership import revoke_leader
from core.exceptions import DomainError


class RoleInline(admin.TabularInline):
    model = Role
    extra = 0
    fields = ("role_name", "is_default", "is_leadership", "is_active", "permissions")
    readonly_fields = ("is_default",)


class ClubDocumentInline(admin.TabularInline):
    model = ClubDocument
    extra = 0
    fields = ("title", "file", "is_public")


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = (
        "acronym",
        "name",
        "faculty",
        "status",
        "leader_enrollment",
        "leader",
        "members_count",
    )
    list_filter = ("status", "faculty", "interest_areas")
    search_fields = ("name", "acronym", "leader_enrollment")
    filter_horizontal = ("interest_areas",)
    readonly_fields = ("created_at", "updated_at", "members_count")
    inlines = [RoleInline, ClubDocumentInline]
    actions = ["revocar_liderazgo"]

    fieldsets = (
        (None, {"fields": ("name", "acronym", "description", "location")}),
        ("Clasificación", {"fields": ("faculty", "interest_areas", "image")}),
        (
            "Liderazgo",
            {
                "fields": ("leader_enrollment", "leader", "status"),
                "description": "El estado y el líder no se editan sueltos: usa "
                "los servicios de asignación/revocación, que mantienen la "
                "membresía directiva y RN-1 en orden.",
            },
        ),
        ("Contacto", {"fields": ("social_media",), "classes": ("collapse",)}),
        ("Auditoría", {"fields": ("created_at", "updated_at", "members_count")}),
    )

    @admin.display(description="miembros activos")
    def members_count(self, obj):
        return obj.members_count

    @admin.action(description="Revocar el liderazgo (deja el club en solo lectura)")
    def revocar_liderazgo(self, request, queryset):
        for club in queryset:
            try:
                revoke_leader(club_id=club.pk)
            except DomainError as exc:
                self.message_user(
                    request, f"{club.acronym}: {exc}", level=messages.ERROR
                )
            else:
                self.message_user(
                    request,
                    f"{club.acronym}: liderazgo revocado.",
                    level=messages.SUCCESS,
                )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("role_name", "club", "is_default", "is_leadership", "is_active")
    list_filter = ("is_default", "is_leadership", "is_active", "club")
    search_fields = ("role_name", "club__acronym")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "club",
        "role",
        "pao_period",
        "status",
        "is_leadership",
        "origin",
    )
    list_filter = ("status", "is_leadership", "origin", "pao_period", "club")
    search_fields = (
        "student__enrollment",
        "student__first_name",
        "student__last_name",
        "club__acronym",
    )
    autocomplete_fields = ("student", "club", "role")
    readonly_fields = ("is_leadership", "created_at", "updated_at")

    def get_queryset(self, request):
        # La lista muestra estudiante, club, rol y período en cada fila: sin
        # esto, cada una dispararía cuatro consultas extra.
        return (
            super()
            .get_queryset(request)
            .select_related("student", "club", "role", "pao_period")
        )


@admin.register(ClubDocument)
class ClubDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "club", "is_public")
    list_filter = ("is_public", "club")
    search_fields = ("title", "club__acronym")
