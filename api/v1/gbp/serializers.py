"""Serializers de trámites ante GBP."""

from rest_framework import serializers

from apps.gbp.models import GbpDocumentProcess


class ProcessSerializer(serializers.ModelSerializer):
    """
    Trámite tal como lo ven GBP y el club que lo envió.

    El ``roster_snapshot`` completo no se incluye: puede tener cientos de filas
    y el buzón muestra decenas de trámites. Se expone solo su tamaño, y el
    detalle tiene su propio endpoint.
    """

    club_acronym = serializers.CharField(source="club.acronym", read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    uploaded_at = serializers.DateTimeField(read_only=True)
    file_url = serializers.SerializerMethodField()
    submitted_by_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    snapshot_size = serializers.IntegerField(read_only=True)

    class Meta:
        model = GbpDocumentProcess
        fields = [
            "id",
            "club",
            "club_acronym",
            "club_name",
            "pao_period",
            "document_type",
            "file_url",
            "status",
            "status_label",
            "uploaded_at",
            "review_feedback",
            "submitted_by_name",
            "reviewed_by_name",
            "reviewed_at",
            "snapshot_size",
        ]
        read_only_fields = fields

    def get_file_url(self, process):
        request = self.context.get("request")
        url = process.file.url if process.file else None
        return request.build_absolute_uri(url) if request and url else url

    def get_submitted_by_name(self, process):
        return (
            process.submitted_by.get_full_name() if process.submitted_by_id else None
        )

    def get_reviewed_by_name(self, process):
        return process.reviewed_by.get_full_name() if process.reviewed_by_id else None


class ProcessDetailSerializer(ProcessSerializer):
    """Detalle con la nómina congelada, que es la evidencia que GBP audita."""

    roster_snapshot = serializers.JSONField(read_only=True)

    class Meta(ProcessSerializer.Meta):
        fields = ProcessSerializer.Meta.fields + ["roster_snapshot"]
        read_only_fields = fields


class SubmitProcessSerializer(serializers.Serializer):
    """F-16 — envío de un trámite."""

    pao_period = serializers.CharField(max_length=10)
    document_type = serializers.CharField(max_length=120)
    file = serializers.FileField()


class ResolveProcessSerializer(serializers.Serializer):
    """F-18 — resolución de GBP. El feedback es obligatorio al rechazar (RN-5)."""

    approved = serializers.BooleanField()
    feedback = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if not attrs["approved"] and not (attrs.get("feedback") or "").strip():
            raise serializers.ValidationError(
                {"feedback": "Debes explicar el motivo del rechazo (RN-5)."}
            )
        return attrs
