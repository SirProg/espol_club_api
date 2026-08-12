from django.contrib import admin

from apps.dynamicforms.models import Form
from apps.dynamicforms.responses import count_responses


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "club",
        "form_type",
        "version",
        "is_active",
        "field_count",
        "response_count",
    )
    list_filter = ("form_type", "is_active", "club")
    search_fields = ("title", "club__acronym")
    readonly_fields = ("version", "root", "created_at", "updated_at", "response_count")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("club")

    @admin.display(description="campos")
    def field_count(self, obj):
        return len(obj.fields or [])

    @admin.display(description="respuestas")
    def response_count(self, obj):
        return count_responses(obj)
