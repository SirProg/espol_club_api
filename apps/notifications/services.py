"""Emisión y lectura de notificaciones (CU-NO1..NO3)."""

from django.db import IntegrityError, transaction

from apps.notifications.models import Notification


def notify(*, user, type, message, target=None, club=None):
    """
    CU-NO3 — crea una notificación, sin duplicar.

    Idempotente por ``(user, type, target)``: los procesos programados del §10
    deben poder ejecutarse dos veces sin llenar el centro de notificaciones de
    avisos repetidos.

    No usa el decorador ``@command`` a propósito: se invoca desde los handlers
    del bus de eventos, que ya corren **después** del commit de la operación de
    negocio. Envolverla en otra transacción no aportaría nada y ocultaría que
    el fallo aquí no debe revertir nada.
    """
    if user is None:
        return None

    target_type = target.__class__.__name__ if target is not None else ""
    target_id = getattr(target, "pk", None) if target is not None else None

    try:
        with transaction.atomic():
            return Notification.objects.create(
                user=user,
                type=type,
                message=message,
                target_type=target_type,
                target_id=target_id,
                club=club,
            )
    except IntegrityError:
        # Ya existía: es exactamente el resultado deseado.
        return Notification.objects.filter(
            user=user, type=type, target_type=target_type, target_id=target_id
        ).first()


def notify_many(*, users, type, message, target=None, club=None):
    """Notifica a varias personas — la bandeja del líder tiene varios titulares."""
    return [
        notify(user=user, type=type, message=message, target=target, club=club)
        for user in users
    ]


def mark_read(*, user, notification_ids=None):
    """
    CU-NO2 — marca como leídas.

    El filtro por ``user`` no es una comodidad: sin él, cualquiera podría marcar
    como leídas las notificaciones de otra persona enviando sus ids.
    """
    queryset = Notification.objects.filter(user=user, read=False)
    if notification_ids:
        queryset = queryset.filter(pk__in=notification_ids)
    return queryset.update(read=True)


def get_user_notifications(user, *, only_unread=False):
    """CU-NO1 — notificaciones del usuario, de la más reciente a la más antigua."""
    if not user or not user.is_authenticated:
        return Notification.objects.none()

    queryset = Notification.objects.filter(user=user).select_related("club")
    if only_unread:
        queryset = queryset.filter(read=False)
    return queryset


def count_unread(user):
    if not user or not user.is_authenticated:
        return 0
    return Notification.objects.filter(user=user, read=False).count()
