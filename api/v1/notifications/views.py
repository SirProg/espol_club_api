"""Centro de notificaciones (RF-51, pantalla 5)."""

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.services import (
    count_unread,
    get_user_notifications,
    mark_read,
)


class NotificationSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    date = serializers.DateTimeField(read_only=True)
    club_acronym = serializers.CharField(source="club.acronym", default=None)

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "type_label",
            "message",
            "read",
            "date",
            "club",
            "club_acronym",
            "target_type",
            "target_id",
        ]
        read_only_fields = fields


class MarkReadSerializer(serializers.Serializer):
    """Sin ids, marca todas las del usuario."""

    ids = serializers.ListField(child=serializers.IntegerField(), required=False)


class NotificationListView(APIView):
    """``GET /api/v1/notifications/`` — las propias, orden descendente."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = get_user_notifications(
            request.user, only_unread=request.query_params.get("unread") == "true"
        )
        return Response(
            {
                "unread_count": count_unread(request.user),
                "results": NotificationSerializer(notifications, many=True).data,
            }
        )


class NotificationReadView(APIView):
    """
    ``POST /api/v1/notifications/read/``.

    El servicio filtra por usuario, así que enviar ids ajenos no marca nada de
    otra persona.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = mark_read(
            user=request.user, notification_ids=serializer.validated_data.get("ids")
        )
        return Response({"marked": updated, "unread_count": count_unread(request.user)})
