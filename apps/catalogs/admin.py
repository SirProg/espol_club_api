from django.contrib import admin

from apps.catalogs.models import Faculty, InterestArea


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("code", "name")
    list_filter = ("is_active",)


@admin.register(InterestArea)
class InterestAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("name",)
    list_filter = ("is_active",)
