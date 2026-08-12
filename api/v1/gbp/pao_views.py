"""
Administración del calendario académico por GBP (RF-45, F-19).

Vive bajo ``/gbp/`` porque GBP es quien lo administra, aunque el modelo esté en
la app ``academic``: el negocio entero consume los períodos, pero configurarlos
es potestad institucional.
"""

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academic import selectors
from apps.academic.models import PaoPeriod
from apps.academic.services import activate_pao, create_pao, update_pao
from core.api.permissions import IsGbpAdmin


class PaoPeriodSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PaoPeriod
        fields = [
            "pao_period",
            "start_date",
            "end_date",
            "status",
            "status_label",
            "sequence",
        ]
        read_only_fields = fields


class PaoWriteSerializer(serializers.Serializer):
    pao_period = serializers.CharField(max_length=10)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    activate = serializers.BooleanField(default=False)


class PaoUpdateSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    activate = serializers.BooleanField(required=False)


class PaoListCreateView(APIView):
    """``GET/POST /api/v1/gbp/pao/`` — V-24."""

    permission_classes = [IsAuthenticated, IsGbpAdmin]

    def get(self, request):
        return Response(PaoPeriodSerializer(selectors.list_paos(), many=True).data)

    def post(self, request):
        serializer = PaoWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        period = create_pao(**serializer.validated_data)
        return Response(
            PaoPeriodSerializer(period).data, status=status.HTTP_201_CREATED
        )


class PaoDetailView(APIView):
    """
    ``PATCH /api/v1/gbp/pao/{pao_period}/``.

    Activar un período **cierra todos los demás** en la misma transacción
    (invariante I-08). El cliente no tiene que cerrarlos uno a uno.
    """

    permission_classes = [IsAuthenticated, IsGbpAdmin]

    def patch(self, request, pao_period):
        serializer = PaoUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        should_activate = data.pop("activate", False)

        if data:
            period = update_pao(pao_period=pao_period, **data)
        else:
            period = selectors.get_pao(pao_period)

        if should_activate:
            period = activate_pao(pao_period)

        return Response(PaoPeriodSerializer(period).data)
