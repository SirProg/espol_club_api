"""
Vistas de solicitudes de membresía (MASTER §16.6).

Dos audiencias con permisos opuestos sobre el mismo recurso: el **estudiante**
crea y consulta las suyas; el **líder** con ``manage_members`` ve la bandeja del
club y resuelve. Por eso las rutas están separadas y cada una declara su propio
permiso, en vez de una sola vista que decidiera por dentro.
"""

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.applications.serializers import (
    ApplicationSerializer,
    CanApplySerializer,
    RejectApplicationSerializer,
    StudentApplicationSerializer,
    SubmitApplicationSerializer,
)
from apps.applications import selectors
from apps.applications.models import MembershipApplication
from apps.applications.services import (
    approve_application,
    can_apply,
    reject_application,
    submit_application,
)
from apps.clubs import policies
from apps.clubs.permissions import ClubPermission
from core.api.permissions import HasClubPermission
from core.api.views import ClubScopedView


class ClubApplicationsView(ClubScopedView):
    """
    ``GET`` bandeja del líder (RF-26) · ``POST`` postular (RF-25).

    Los dos métodos conviven en la misma URL porque es el mismo recurso, pero
    exigen permisos distintos: leer la bandeja requiere ``manage_members``,
    postular solo estar autenticado. La comprobación es explícita en cada uno.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, club_id):
        if not policies.has_club_permission(
            request.user, club_id, ClubPermission.MANAGE_MEMBERS
        ):
            raise PermissionDenied(
                "Solo la directiva del club puede ver las solicitudes recibidas."
            )

        applications = selectors.get_club_applications(
            club_id, status=request.query_params.get("status")
        )
        return Response(ApplicationSerializer(applications, many=True).data)

    def post(self, request, club_id):
        serializer = SubmitApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application = submit_application(
            student=request.user,
            club_id=club_id,
            responses=serializer.validated_data["responses"],
        )
        return Response(
            StudentApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class CanApplyView(ClubScopedView):
    """
    ``GET /api/v1/clubs/{club_id}/applications/can-apply/`` — RN-2.

    Le permite a la app pintar el botón deshabilitado con el motivo, en vez de
    dejar que el estudiante llene el formulario para recibir un rechazo al
    enviarlo.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, club_id):
        verdict = can_apply(request.user, club_id)
        return Response(CanApplySerializer(verdict).data)


class MyApplicationsView(APIView):
    """``GET /api/v1/students/me/applications/`` — historial propio (RF-50)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        applications = selectors.get_student_applications(request.user)
        return Response(StudentApplicationSerializer(applications, many=True).data)


class ApplicationResolutionView(APIView):
    """
    ``POST /api/v1/applications/{id}/approve|reject/`` — RF-27.

    Disponible también desde la app móvil como conveniencia del líder (RF-57):
    es la misma operación, no una versión reducida.
    """

    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            MembershipApplication.objects.select_related("club", "student"),
            pk=self.kwargs["application_id"],
        )

    def post(self, request, application_id, action):
        application = self.get_object()

        if not policies.has_club_permission(
            request.user, application.club_id, ClubPermission.MANAGE_MEMBERS
        ):
            raise PermissionDenied(
                "Tu rol en el club no incluye el permiso para resolver solicitudes."
            )

        if action == "approve":
            resolved = approve_application(
                application_id=application.pk, resolved_by=request.user
            )
        else:
            serializer = RejectApplicationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            resolved = reject_application(
                application_id=application.pk,
                resolved_by=request.user,
                feedback=serializer.validated_data["feedback"],
            )

        return Response(ApplicationSerializer(resolved).data)
