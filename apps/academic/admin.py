from django.contrib import admin, messages

from apps.academic.models import PaoPeriod
from apps.academic.services import activate_pao
from core.exceptions import DomainError


@admin.register(PaoPeriod)
class PaoPeriodAdmin(admin.ModelAdmin):
    list_display = ("pao_period", "start_date", "end_date", "status", "sequence")
    list_filter = ("status",)
    search_fields = ("pao_period",)
    ordering = ("-sequence",)
    readonly_fields = ("sequence", "created_at", "updated_at")
    actions = ["activar_periodo"]

    def get_readonly_fields(self, request, obj=None):
        # La PK está referenciada por membresías y trámites: es inmutable una
        # vez creada.
        fields = super().get_readonly_fields(request, obj)
        return (*fields, "pao_period") if obj else fields

    @admin.action(description="Activar el período seleccionado (cierra los demás)")
    def activar_periodo(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                "Selecciona exactamente un período para activar.",
                level=messages.ERROR,
            )
            return
        period = queryset.first()
        try:
            activate_pao(period.pk)
        except DomainError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
        else:
            self.message_user(
                request,
                f"Período {period.pk} activado. Los demás quedaron cerrados.",
                level=messages.SUCCESS,
            )
