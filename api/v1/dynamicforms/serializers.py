"""Serializers de formularios dinámicos."""

from rest_framework import serializers

from apps.dynamicforms.models import Form
from apps.dynamicforms.responses import count_responses
from apps.dynamicforms.schema import FieldType


class FormFieldSerializer(serializers.Serializer):
    """
    Un campo del esquema.

    Documenta el contrato de cara al constructor de formularios, pero **no es la
    validación autoritativa**: esa vive en ``dynamicforms.schema``, que también
    se aplica desde el admin y desde el shell. Aquí se valida la forma para
    poder devolver errores por campo antes de llamar al servicio.
    """

    field_id = serializers.CharField(max_length=60)
    label = serializers.CharField(max_length=255)
    type = serializers.ChoiceField(choices=FieldType.choices)
    required = serializers.BooleanField(default=False)
    order = serializers.IntegerField(default=0)
    options = serializers.ListField(
        child=serializers.CharField(max_length=255), required=False, default=list
    )
    validation = serializers.DictField(required=False, default=dict)


class FormSerializer(serializers.ModelSerializer):
    """Lectura de un formulario, incluido lo que el líder necesita para decidir."""

    club_acronym = serializers.CharField(source="club.acronym", read_only=True)
    form_type_label = serializers.CharField(
        source="get_form_type_display", read_only=True
    )
    family_id = serializers.IntegerField(read_only=True)
    response_count = serializers.SerializerMethodField()
    is_editable = serializers.SerializerMethodField()

    class Meta:
        model = Form
        fields = [
            "id",
            "club",
            "club_acronym",
            "form_type",
            "form_type_label",
            "title",
            "fields",
            "version",
            "is_active",
            "family_id",
            "response_count",
            "is_editable",
            "created_at",
        ]
        read_only_fields = fields

    def get_response_count(self, form):
        return count_responses(form)

    def get_is_editable(self, form):
        """
        Le dice al panel si debe ofrecer 'Editar' o 'Crear nueva versión'.

        Es una conveniencia de presentación: el servidor rechaza la edición de
        todos modos (RF-24), pero ofrecer un botón que siempre falla es una
        mala interfaz.
        """
        return count_responses(form) == 0


class FormSchemaSerializer(serializers.ModelSerializer):
    """
    Lo mínimo para **renderizar** el formulario en la app móvil (RF-23).

    Deja fuera los contadores y las banderas de gestión: el estudiante que va a
    postular no necesita saber cuántas respuestas lleva el formulario.
    """

    class Meta:
        model = Form
        fields = ["id", "title", "form_type", "version", "fields"]
        read_only_fields = fields


class FormWriteSerializer(serializers.Serializer):
    """Alta de un formulario o de una versión nueva (F-12)."""

    form_type = serializers.ChoiceField(choices=Form.FormType.choices)
    title = serializers.CharField(max_length=150)
    fields = FormFieldSerializer(many=True)

    def validate_fields(self, value):
        if not value:
            raise serializers.ValidationError(
                "El formulario debe tener al menos un campo."
            )
        return value


class FormUpdateSerializer(serializers.Serializer):
    """Edición en sitio o creación de versión: mismos datos, distinta operación."""

    title = serializers.CharField(max_length=150, required=False)
    fields = FormFieldSerializer(many=True, required=False)


class SubmissionPreviewSerializer(serializers.Serializer):
    """
    Comprobación de respuestas sin llegar a guardarlas.

    Permite al cliente validar contra el servidor antes de confirmar, y sirve de
    prueba directa de CU-FO6 sin tener que crear una postulación.
    """

    responses = serializers.JSONField()
