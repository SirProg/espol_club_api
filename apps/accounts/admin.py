from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm

from apps.accounts.models import Student


@admin.register(Student)
class StudentAdmin(UserAdmin):
    """
    Admin del usuario adaptado a la matrícula.

    Los fieldsets de UserAdmin referencian ``username``, que este modelo no
    tiene: hay que redefinirlos por completo, no extenderlos.
    """

    change_password_form = AdminPasswordChangeForm
    ordering = ("last_name", "first_name")
    list_display = (
        "enrollment",
        "get_full_name",
        "email",
        "faculty",
        "is_gbp_admin",
        "is_verified",
        "is_active",
    )
    list_filter = ("is_gbp_admin", "is_verified", "is_active", "is_staff", "faculty")
    search_fields = ("enrollment", "first_name", "last_name", "email")
    readonly_fields = ("last_login", "created_at", "updated_at", "age")

    fieldsets = (
        (None, {"fields": ("enrollment", "password")}),
        (
            "Datos personales",
            {"fields": ("first_name", "last_name", "email", "birth_date", "age")},
        ),
        ("Datos académicos", {"fields": ("faculty", "career", "semester")}),
        (
            "Perfil público",
            {
                "fields": ("description", "skills", "social_media"),
                "classes": ("collapse",),
            },
        ),
        (
            "Estado y permisos",
            {
                "fields": (
                    "is_gbp_admin",
                    "is_verified",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Auditoría", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "enrollment",
                    "first_name",
                    "last_name",
                    "email",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    @admin.display(description="nombre")
    def get_full_name(self, obj):
        return obj.get_full_name()

    @admin.display(description="edad")
    def age(self, obj):
        return obj.age if obj.age is not None else "—"
