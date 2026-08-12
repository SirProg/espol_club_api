"""
Vistas del constructor de formularios (MASTER §16.6).

RF-53 lo dice explícitamente: los formularios se diseñan **solo** desde el panel
web. La app móvil actúa como cliente que renderiza y envía respuestas, así que
solo consume los endpoints de lectura del esquema.
"""

from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.dynamicforms.serializers import (
    FormSchemaSerializer,
    FormSerializer,
    FormUpdateSerializer,
    FormWriteSerializer,
    SubmissionPreviewSerializer,
)
from apps.clubs import policies
from apps.clubs.permissions import ClubPermission
from apps.dynamicforms import selectors
from apps.dynamicforms.models import Form
from apps.dynamicforms.services import (
    activate_form,
    create_form,
    create_new_version,
    deactivate_form,
    delete_form,
    update_form,
    validate_submission,
)
from core.api.permissions import HasClubPermission
from core.api.views import ClubScopedView


class ClubFormListCreateView(ClubScopedView):
    """``GET/POST /api/v1/clubs/{club_id}/forms/`` — RF-22."""

    permission_classes = [IsAuthenticated, HasClubPermission]
    required_club_permission = ClubPermission.MANAGE_FORMS

    def get(self, request, club_id):
        forms = selectors.get_club_forms(
            club_id,
            form_type=request.query_params.get("form_type"),
            only_active=request.query_params.get("only_active") == "true",
        )
        return Response(FormSerializer(forms, many=True).data)

    def post(self, request, club_id):
        serializer = FormWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        form = create_form(
            club_id=club_id,
            form_type=serializer.validated_data["form_type"],
            title=serializer.validated_data["title"],
            fields=serializer.validated_data["fields"],
        )
        return Response(
            FormSerializer(form).data, status=status.HTTP_201_CREATED
        )


class MembershipFormView(ClubScopedView):
    """
    ``GET /api/v1/clubs/{club_id}/forms/membership/`` — RF-25.

    Abierto a cualquier autenticado: es el formulario que el estudiante debe
    poder ver **antes** de ser miembro, porque es justamente el que usa para
    postular.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, club_id):
        form = selectors.get_active_membership_form(club_id)
        if form is None:
            return Response(
                {
                    "error": {
                        "code": "no_membership_form",
                        "message": (
                            "Este club todavía no ha publicado un formulario de "
                            "postulación."
                        ),
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(FormSchemaSerializer(form).data)


class FormDetailView(APIView):
    """``GET/PATCH/DELETE /api/v1/forms/{form_id}/``."""

    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(Form.objects.select_related("club"), pk=self.kwargs["form_id"])

    def get(self, request, form_id):
        form = self.get_object()

        # Quien gestiona formularios ve la ficha completa; el resto solo el
        # esquema que necesita para renderizar (RF-23).
        if policies.has_club_permission(
            request.user, form.club_id, ClubPermission.MANAGE_FORMS
        ):
            return Response(FormSerializer(form).data)
        if not form.is_active:
            return Response(
                {
                    "error": {
                        "code": "form_inactive",
                        "message": "Este formulario ya no está disponible.",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(FormSchemaSerializer(form).data)

    def patch(self, request, form_id):
        """
        Edición en sitio. Devuelve **409** si el formulario ya tiene respuestas,
        con la indicación de crear una versión nueva (RF-24).
        """
        form = self.get_object()
        self._assert_can_manage(request, form)

        serializer = FormUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated = update_form(form_id=form.pk, **serializer.validated_data)
        return Response(FormSerializer(updated).data)

    def delete(self, request, form_id):
        form = self.get_object()
        self._assert_can_manage(request, form)

        delete_form(form_id=form.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _assert_can_manage(self, request, form):
        from rest_framework.exceptions import PermissionDenied

        if not policies.has_club_permission(
            request.user, form.club_id, ClubPermission.MANAGE_FORMS
        ):
            raise PermissionDenied(
                "Tu rol en el club no incluye el permiso para gestionar formularios."
            )


class FormVersionView(FormDetailView):
    """
    ``POST /api/v1/forms/{form_id}/versions/`` — la salida al 409.

    Crea la versión siguiente y desactiva la anterior, dejando intactas las
    respuestas que ya apuntaban a ella.
    """

    def post(self, request, form_id):
        form = self.get_object()
        self._assert_can_manage(request, form)

        serializer = FormUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        new_version = create_new_version(form_id=form.pk, **serializer.validated_data)
        return Response(
            FormSerializer(new_version).data, status=status.HTTP_201_CREATED
        )


class FormActivationView(FormDetailView):
    """``POST /api/v1/forms/{form_id}/activate|deactivate/``."""

    def post(self, request, form_id):
        form = self.get_object()
        self._assert_can_manage(request, form)

        action = self.kwargs["action"]
        updated = (
            activate_form(form_id=form.pk)
            if action == "activate"
            else deactivate_form(form_id=form.pk)
        )
        return Response(FormSerializer(updated).data)


class FormValidateView(FormDetailView):
    """
    ``POST /api/v1/forms/{form_id}/validate/`` — CU-FO6 sin efectos.

    Comprueba unas respuestas contra el esquema y devuelve cómo quedarían
    normalizadas, sin guardar nada. La app la usa para validar antes de
    confirmar el envío.
    """

    def post(self, request, form_id):
        form = self.get_object()

        serializer = SubmissionPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        normalized = validate_submission(form, serializer.validated_data["responses"])
        return Response({"valid": True, "responses": normalized})
