from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "club", "read", "created_at")
    list_filter = ("type", "read", "club")
    search_fields = ("user__enrollment", "message")
    readonly_fields = tuple(
        field.name for field in Notification._meta.fields if field.name != "read"
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "club")

    def has_add_permission(self, request):
        # Las notificaciones nacen de eventos de dominio, no de altas manuales.
        return False
