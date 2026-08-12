"""Vistas del buzón de GBP y de la rendición de cuentas del club."""

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.gbp.serializers import (
    ProcessDetailSerializer,
    ProcessSerializer,
    ResolveProcessSerializer,
    SubmitProcessSerializer,
)
from apps.clubs import policies
from apps.clubs.permissions import ClubPermission
from apps.gbp import selectors
from apps.gbp.models import GbpDocumentProcess
from apps.gbp.services import (
    get_history_by_pao,
    resolve_process,
    submit_process,
    take_process,
)
from core.api.permissions import IsGbpAdmin
from core.api.views import ClubScopedView


class ClubProcessesView(ClubScopedView):
    """``GET/POST /api/v1/clubs/{club_id}/processes/`` — RF-40 (V-20)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, club_id):
        if not policies.can_see_roster(request.user, club_id):
            raise PermissionDenied(
                "Los trámites del club son información interna."
            )
        return Response(
            ProcessSerializer(
                selectors.get_club_processes(club_id),
                many=True,
                context={"request": request},
            ).data
        )

    def post(self, request, club_id):
        if not policies.has_club_permission(
            request.user, club_id, ClubPermission.SUBMIT_GBP_REPORTS
        ):
            raise PermissionDenied(
                "Tu rol en el club no incluye el permiso para enviar trámites a GBP."
            )

        serializer = SubmitProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        process = submit_process(
            club_id=club_id, submitted_by=request.user, **serializer.validated_data
        )
        return Response(
            ProcessSerializer(process, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class GbpInboxView(APIView):
    """``GET /api/v1/gbp/processes/`` — buzón de trámites (V-23)."""

    permission_classes = [IsAuthenticated, IsGbpAdmin]

    def get(self, request):
        processes = selectors.get_inbox(
            status=request.query_params.get("status"),
            pao_period=request.query_params.get("pao"),
            club_id=request.query_params.get("club"),
        )
        return Response(
            ProcessSerializer(
                processes, many=True, context={"request": request}
            ).data
        )


class ProcessDetailView(APIView):
    """
    ``GET /api/v1/gbp/processes/{id}/`` — la ficha con la nómina congelada.

    La lee GBP para auditar, y el club para ver qué envió. Ambos ven lo mismo:
    es la evidencia que ya está fijada.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, process_id):
        process = get_object_or_404(
            GbpDocumentProcess.objects.select_related("club"), pk=process_id
        )
        if not (
            policies.is_gbp_admin(request.user)
            or policies.can_see_roster(request.user, process.club_id)
        ):
            raise PermissionDenied("Este trámite no es de tu club.")

        return Response(
            ProcessDetailSerializer(process, context={"request": request}).data
        )


class ProcessReviewView(APIView):
    """
    ``POST /api/v1/gbp/processes/{id}/take|review/`` — CU-GB3..GB5.

    ``take`` marca ``Under Review`` explícitamente (PPD-05) y ``review``
    resuelve. Son dos pasos y no uno porque el primero deja constancia de quién
    asumió la revisión antes de decidir.
    """

    permission_classes = [IsAuthenticated, IsGbpAdmin]

    def post(self, request, process_id, action):
        if action == "take":
            process = take_process(process_id=process_id, reviewer=request.user)
        else:
            serializer = ResolveProcessSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            process = resolve_process(
                process_id=process_id,
                reviewer=request.user,
                approved=serializer.validated_data["approved"],
                feedback=serializer.validated_data.get("feedback", ""),
            )

        return Response(ProcessSerializer(process, context={"request": request}).data)


class ProcessExportView(APIView):
    """
    ``GET /api/v1/gbp/processes/{id}/export/?format=xlsx`` — RF-42.

    Descarga la nómina **congelada** del trámite, no la actual. Dos descargas
    separadas por meses producen el mismo contenido: eso es lo que la convierte
    en evidencia y no en un reporte.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, process_id):
        from django.http import HttpResponse

        from apps.gbp.exports import export_process

        process = get_object_or_404(
            GbpDocumentProcess.objects.select_related("club", "reviewed_by"),
            pk=process_id,
        )
        if not (
            policies.is_gbp_admin(request.user)
            or policies.can_see_roster(request.user, process.club_id)
        ):
            raise PermissionDenied("Este trámite no es de tu club.")

        contenido, content_type, filename = export_process(
            process, request.query_params.get("format", "xlsx")
        )
        response = HttpResponse(contenido, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class GbpConsolidatedExportView(APIView):
    """``GET /api/v1/gbp/processes/export/?pao=2026-I`` — consolidado (CU-GB6)."""

    permission_classes = [IsAuthenticated, IsGbpAdmin]

    def get(self, request):
        from django.http import HttpResponse

        from apps.gbp.exports import (
            assert_supported_format,
            export_consolidated_xlsx,
        )

        fmt = request.query_params.get("format", "xlsx")
        assert_supported_format(fmt)
        if fmt != "xlsx":
            return Response(
                {
                    "error": {
                        "code": "unsupported_export_format",
                        "message": (
                            "El consolidado de trámites solo se exporta en "
                            ".xlsx: es una tabla, no un documento de texto."
                        ),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        processes = selectors.get_inbox(
            status=request.query_params.get("status"),
            pao_period=request.query_params.get("pao"),
        )
        response = HttpResponse(
            export_consolidated_xlsx(processes),
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = (
            'attachment; filename="tramites-consolidado.xlsx"'
        )
        return response


class GbpHistoryView(APIView):
    """``GET /api/v1/gbp/history/?pao=2025-II`` — RF-49 (V-25)."""

    permission_classes = [IsAuthenticated, IsGbpAdmin]

    def get(self, request):
        pao_period = request.query_params.get("pao")
        if not pao_period:
            return Response(
                {
                    "error": {
                        "code": "missing_pao",
                        "message": "Indica el período con ?pao=2026-I.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"pao_period": pao_period, "clubs": get_history_by_pao(pao_period)}
        )
