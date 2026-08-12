"""
Vistas de eventos, credenciales y asistencia (MASTER §16.6).

Tres audiencias sobre el mismo dominio: el **estudiante** explora e inscribe, el
**líder** gestiona y consulta métricas, y el **staff** escanea. Cada una tiene
su ruta y su permiso, en vez de una vista que decidiera por dentro.
"""

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.events.serializers import (
    CredentialSerializer,
    EventDetailSerializer,
    EventListSerializer,
    EventManagementSerializer,
    EventStaffMemberSerializer,
    EventWriteSerializer,
    RegisterForEventSerializer,
    RegistrationLogSerializer,
    ScanSerializer,
    SetEventStaffSerializer,
)
from apps.clubs import policies
from apps.clubs.permissions import ClubPermission
from apps.events import selectors
from apps.events.models import Event
from apps.events.services.attendance import describe_scan_result, register_scan
from apps.events.services.events import (
    can_register,
    create_event,
    delete_event,
    set_event_staff,
    update_event,
)
from apps.events.services.registration import register_for_event
from core.api.views import ClubScopedView


class EventListView(APIView):
    """
    ``GET /api/v1/events/`` — CU-EV4 (RF-31).

    Devuelve **todos** los eventos, incluidos los ``MembersOnly``. No es un
    descuido: el bloqueo está en el registro, no en la visibilidad.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        events = selectors.get_visible_events(
            request.user,
            club_id=request.query_params.get("club"),
            upcoming_only=request.query_params.get("upcoming") == "true",
        )
        return Response(EventListSerializer(events, many=True).data)


class EventDetailView(APIView):
    """``GET/PATCH/DELETE /api/v1/events/{event_id}/``."""

    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            Event.objects.select_related("club", "registration_form"),
            pk=self.kwargs["event_id"],
        )

    def get(self, request, event_id):
        event = selectors.get_event(event_id)
        if event is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer_class = (
            EventManagementSerializer
            if policies.has_club_permission(
                request.user, event.club_id, ClubPermission.MANAGE_EVENTS
            )
            else EventDetailSerializer
        )
        return Response(serializer_class(event, context={"request": request}).data)

    def patch(self, request, event_id):
        event = self.get_object()
        self._assert_can_manage(request, event)

        serializer = EventWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        data = dict(serializer.validated_data)
        form_id = data.pop("registration_form_id", ...)
        updated = update_event(
            event_id=event.pk, registration_form_id=form_id, **data
        )
        return Response(
            EventManagementSerializer(updated, context={"request": request}).data
        )

    def delete(self, request, event_id):
        event = self.get_object()
        self._assert_can_manage(request, event)

        delete_event(event_id=event.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _assert_can_manage(self, request, event):
        if not policies.has_club_permission(
            request.user, event.club_id, ClubPermission.MANAGE_EVENTS
        ):
            raise PermissionDenied(
                "Tu rol en el club no incluye el permiso para gestionar eventos."
            )


class ClubEventsView(ClubScopedView):
    """``GET/POST /api/v1/clubs/{club_id}/events/`` — CU-EV1, CU-EV11 (RF-38)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, club_id):
        if not policies.has_club_permission(
            request.user, club_id, ClubPermission.MANAGE_EVENTS
        ):
            raise PermissionDenied(
                "Las métricas de los eventos son de la directiva del club."
            )

        events = selectors.get_club_events(club_id)
        return Response(
            EventManagementSerializer(
                events, many=True, context={"request": request}
            ).data
        )

    def post(self, request, club_id):
        if not policies.has_club_permission(
            request.user, club_id, ClubPermission.MANAGE_EVENTS
        ):
            raise PermissionDenied(
                "Tu rol en el club no incluye el permiso para crear eventos."
            )

        serializer = EventWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = create_event(club_id=club_id, **serializer.validated_data)
        return Response(
            EventManagementSerializer(event, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class EventStaffView(EventDetailView):
    """``GET/PUT /api/v1/events/{event_id}/staff/`` — RF-35."""

    def get(self, request, event_id):
        event = self.get_object()
        self._assert_can_manage(request, event)

        return Response(
            EventStaffMemberSerializer(
                selectors.get_event_staff(event_id), many=True
            ).data
        )

    def put(self, request, event_id):
        event = self.get_object()
        self._assert_can_manage(request, event)

        serializer = SetEventStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        staff = set_event_staff(
            event_id=event.pk,
            student_ids=serializer.validated_data["student_ids"],
            assigned_by=request.user,
        )
        return Response(EventStaffMemberSerializer(staff, many=True).data)


class EventRegistrationView(APIView):
    """``POST /api/v1/events/{event_id}/register/`` — CU-EV7 (RF-32)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        serializer = RegisterForEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration = register_for_event(
            student=request.user,
            event_id=event_id,
            responses=serializer.validated_data["responses"],
        )
        return Response(
            CredentialSerializer(registration).data, status=status.HTTP_201_CREATED
        )


class CanRegisterView(APIView):
    """``GET /api/v1/events/{event_id}/can-register/`` — CU-EV5 (RF-34)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = get_object_or_404(
            Event.objects.select_related("club"), pk=event_id
        )
        return Response(can_register(request.user, event))


class EventRegistrationLogView(EventDetailView):
    """
    ``GET /api/v1/events/{event_id}/registrations/`` — bitácora (pantalla 34).

    Resuelve PPD-04: la bitácora es la lista de inscritos de un evento
    **seleccionable**. La deuda de MASTER §20.10 era que la Fase 1 mostraba
    siempre el primer evento del club, sin selector; aquí el evento va en la
    URL, así que el selector es del cliente.
    """

    def get(self, request, event_id):
        event = self.get_object()
        self._assert_can_manage(request, event)

        registrations = selectors.get_event_registrations(event_id)
        return Response(
            {
                "event": {
                    "id": event.pk,
                    "event_name": event.event_name,
                    "start_datetime": event.start_datetime,
                },
                "summary": selectors.event_attendance_summary(event_id),
                "registrations": RegistrationLogSerializer(
                    registrations,
                    many=True,
                    context={
                        "include_responses": request.query_params.get("responses")
                        == "true"
                    },
                ).data,
            }
        )


class MyCredentialsView(APIView):
    """``GET /api/v1/students/me/registrations/`` — pantalla 12."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        registrations = selectors.get_student_registrations(
            request.user,
            only_usable=request.query_params.get("usable") == "true",
        )
        return Response(CredentialSerializer(registrations, many=True).data)


class AttendanceScanView(APIView):
    """
    ``POST /api/v1/attendance/scan/`` — CU-EV9 (RN-6, RF-36).

    La vista es deliberadamente delgada: toda la cadena de guardas, el bloqueo
    de fila y la transacción viven en el servicio, porque el escaneo también
    debe poder ejecutarse desde un comando o una prueba sin pasar por HTTP.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attendance = register_scan(
            qr_token=serializer.validated_data["qr_token"],
            staff_student=request.user,
        )
        return Response(describe_scan_result(attendance))
