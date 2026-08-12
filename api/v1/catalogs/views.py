"""
Catálogos cerrados del sistema.

Los consumen el formulario de registro (facultades) y el filtro del catálogo de
clubes (áreas de interés). Se exponen sin autenticación: son datos públicos e
institucionales, y el formulario de registro los necesita **antes** de que
exista una cuenta.
"""

from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academic.selectors import get_active_pao_or_none, list_paos
from apps.catalogs.models import Faculty, InterestArea


class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ["id", "code", "name"]


class InterestAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestArea
        fields = ["id", "name"]


class PaoPeriodSerializer(serializers.Serializer):
    pao_period = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    status = serializers.CharField()
    status_label = serializers.CharField(source="get_status_display")


class CatalogsView(APIView):
    """
    ``GET /api/v1/catalogs/`` — todo lo que el cliente necesita para pintar
    selects, en una sola petición.

    Va junto y no en tres endpoints porque el registro y el catálogo los piden a
    la vez, y tres viajes para tres listas cortas es peor que uno.
    """

    permission_classes = [AllowAny]
    # Datos estáticos y pequeños: no tiene sentido paginarlos.
    pagination_class = None

    def get(self, request):
        active_pao = get_active_pao_or_none()
        return Response(
            {
                "faculties": FacultySerializer(
                    Faculty.objects.filter(is_active=True), many=True
                ).data,
                "interest_areas": InterestAreaSerializer(
                    InterestArea.objects.filter(is_active=True), many=True
                ).data,
                "pao_periods": PaoPeriodSerializer(list_paos(), many=True).data,
                "active_pao": active_pao.pao_period if active_pao else None,
            }
        )
