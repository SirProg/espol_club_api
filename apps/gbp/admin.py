from django.contrib import admin

from apps.gbp.models import GbpDocumentProcess


@admin.register(GbpDocumentProcess)
class GbpDocumentProcessAdmin(admin.ModelAdmin):
    list_display = (
        "document_type",
        "club",
        "pao_period",
        "status",
        "created_at",
        "reviewed_by",
        "snapshot_size",
    )
    list_filter = ("status", "pao_period", "club")
    search_fields = ("document_type", "club__acronym")
    readonly_fields = (
        "roster_snapshot",
        "submitted_by",
        "created_at",
        "updated_at",
        "snapshot_size",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("club", "pao_period", "submitted_by", "reviewed_by")
        )

    @admin.display(description="miembros en la nómina congelada")
    def snapshot_size(self, obj):
        return obj.snapshot_size
