"""
Vistas de clubes, roles, nómina y documentos.

La elección de serializer según el actor (§16.7) ocurre en ``get_serializer_class``
o su equivalente explícito en cada vista, nunca dentro del serializer.
"""

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.clubs.serializers import (
    AssignLeaderSerializer,
    ClubCreateSerializer,
    ClubDocumentSerializer,
    ClubInternalSerializer,
    ClubPublicSerializer,
    ClubWriteSerializer,
    DocumentUploadSerializer,
    DocumentVisibilitySerializer,
    MembershipRoleSerializer,
    MembershipSerializer,
    RenewRosterSerializer,
    RoleSerializer,
    RoleWriteSerializer,
)
from apps.catalogs.models import Faculty
from apps.clubs import policies, selectors
from apps.clubs.models import Club, ClubDocument, Role
from apps.clubs.permissions import ClubPermission
from apps.clubs.services.clubs import (
    add_club_document,
    create_club,
    delete_club_document,
    set_document_visibility,
    update_club,
)
from apps.clubs.services.leadership import assign_leader, revoke_leader
from apps.clubs.services.memberships import (
    renew_roster,
    revoke_membership,
    set_membership_role,
)
from apps.clubs.services.roles import (
    create_role,
    deactivate_role,
    delete_role,
    update_role,
)
from core.api.permissions import IsGbpAdmin
from core.api.views import ClubScopedView


class ClubListCreateView(APIView):
    """
    ``GET`` catálogo filtrable (RF-46) · ``POST`` alta por GBP (RF-11).

    El catálogo es la funcionalidad que MASTER §1.3 declara prioritaria: si los
    estudiantes no encuentran los clubes, lo demás no importa.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        clubs = selectors.list_clubs(
            search=request.query_params.get("q"),
            faculty_id=request.query_params.get("faculty"),
            interest_area_id=request.query_params.get("area"),
        )
        # El catálogo es siempre la proyección pública, incluso para un miembro:
        # es una lista de descubrimiento, no la ficha interna de cada club.
        return Response(
            ClubPublicSerializer(clubs, many=True, context={"request": request}).data
        )

    def post(self, request):
        if not policies.is_gbp_admin(request.user):
            raise PermissionDenied(
                "Solo GBP puede dar de alta clubes (RF-11)."
            )

        serializer = ClubCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)

        club = create_club(
            name=data["name"],
            acronym=data["acronym"],
            description=data["description"],
            location=data["location"],
            leader_enrollment=data["leader_enrollment"],
            faculty=_resolve_faculty(data.get("faculty_id")),
            interest_area_ids=data["interest_area_ids"],
            image=data.get("image", ""),
            social_media=data.get("social_media"),
        )
        return Response(
            ClubInternalSerializer(club, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ClubDetailView(ClubScopedView):
    """
    ``GET/PATCH /api/v1/clubs/{club_id}/``.

    **Prueba de aceptación de MASTER §16.7:** un GET hecho por un estudiante que
    no es miembro nunca debe contener nombres ni correos de miembros. Se cumple
    eligiendo aquí la clase, no filtrando después.
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self, request, club_id):
        if policies.can_see_roster(request.user, club_id):
            return ClubInternalSerializer
        return ClubPublicSerializer

    def get(self, request, club_id):
        club = selectors.get_club(club_id)
        if club is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer_class = self.get_serializer_class(request, club_id)
        return Response(serializer_class(club, context={"request": request}).data)

    def patch(self, request, club_id):
        if not policies.has_club_permission(
            request.user, club_id, ClubPermission.MANAGE_CLUB_INFO
        ):
            raise PermissionDenied(
                "Tu rol en el club no incluye el permiso para editar su información."
            )

        serializer = ClubWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)

        faculty = (
            _resolve_faculty(data.pop("faculty_id"))
            if "faculty_id" in data
            else ...
        )
        club = update_club(club_id=club_id, faculty=faculty, **data)
        return Response(
            ClubInternalSerializer(
                selectors.get_club(club.pk), context={"request": request}
            ).data
        )


class ClubMembersView(ClubScopedView):
    """``GET /api/v1/clubs/{club_id}/members/`` — RF-48."""

    permission_classes = [IsAuthenticated]

    def get(self, request, club_id):
        if not policies.can_see_roster(request.user, club_id):
            raise PermissionDenied(
                "La lista de miembros solo está disponible para el club y para GBP."
            )

        members = selectors.get_club_members(
            club_id,
            only_active=request.query_params.get("all") != "true",
            pao_period=request.query_params.get("pao"),
        )
        return Response(MembershipSerializer(members, many=True).data)


class ClubRosterView(ClubScopedView):
    """``GET/POST /api/v1/clubs/{club_id}/nomina/`` — RF-39, RF-21."""

    permission_classes = [IsAuthenticated]

    def get(self, request, club_id):
        if not policies.can_see_roster(request.user, club_id):
            raise PermissionDenied("La nómina es del club y de GBP.")

        pao = request.query_params.get("pao")
        roster = selectors.get_roster(club_id, pao) if pao else selectors.get_club_members(club_id)
        return Response(MembershipSerializer(roster, many=True).data)

    def post(self, request, club_id):
        """Renovación de la nómina al PAO vigente (RF-21, transición M5)."""
        if not policies.has_club_permission(
            request.user, club_id, ClubPermission.MANAGE_MEMBERS
        ):
            raise PermissionDenied(
                "Tu rol en el club no incluye el permiso para renovar la nómina."
            )

        serializer = RenewRosterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = renew_roster(
            club_id=club_id,
            membership_ids=serializer.validated_data["membership_ids"],
            pao_period=None,
        )
        return Response(
            {
                "renewed": MembershipSerializer(result["renewed"], many=True).data,
                "skipped": [m.pk for m in result["skipped"]],
            }
        )


class ClubRolesView(ClubScopedView):
    """``GET/POST /api/v1/clubs/{club_id}/roles/`` — RF-06, RF-07."""

    permission_classes = [IsAuthenticated]

    def get(self, request, club_id):
        if not policies.can_see_roster(request.user, club_id):
            raise PermissionDenied("Los roles del club son información interna.")

        roles = selectors.get_club_roles(
            club_id, only_active=request.query_params.get("all") != "true"
        )
        return Response(RoleSerializer(roles, many=True).data)

    def post(self, request, club_id):
        if not policies.has_club_permission(
            request.user, club_id, ClubPermission.MANAGE_ROLES
        ):
            raise PermissionDenied(
                "Solo quien tiene 'manage_roles' puede crear roles (RN-7)."
            )

        serializer = RoleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = create_role(club_id=club_id, **serializer.validated_data)
        return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)


class RoleDetailView(APIView):
    """``PATCH/DELETE /api/v1/roles/{role_id}/``."""

    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            Role.objects.select_related("club"), pk=self.kwargs["role_id"]
        )

    def patch(self, request, role_id):
        role = self.get_object()
        self._assert_can_manage(request, role.club_id)

        serializer = RoleWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated = update_role(role_id=role.pk, **serializer.validated_data)
        return Response(RoleSerializer(updated).data)

    def delete(self, request, role_id):
        """
        Borra el rol si nunca tuvo uso; si lo tuvo, lo desactiva (D-13).

        El cliente no tiene que saber cuál de las dos aplica: pide retirar el
        rol y el servidor conserva el historial cuando hace falta.
        """
        role = self.get_object()
        self._assert_can_manage(request, role.club_id)

        from apps.clubs.services.roles import is_role_in_use

        if is_role_in_use(role.pk):
            deactivate_role(role_id=role.pk)
            return Response(
                {
                    "deactivated": True,
                    "message": (
                        "El rol tiene membresías asociadas: se desactivó en vez de "
                        "eliminarse para conservar el historial."
                    ),
                }
            )

        delete_role(role_id=role.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _assert_can_manage(self, request, club_id):
        if not policies.has_club_permission(
            request.user, club_id, ClubPermission.MANAGE_ROLES
        ):
            raise PermissionDenied(
                "Tu rol en el club no incluye el permiso para gestionar roles."
            )


class MembershipDetailView(APIView):
    """``PATCH /api/v1/memberships/{id}/`` · ``POST .../revoke/`` — RF-09, RF-19."""

    permission_classes = [IsAuthenticated]

    def get_object(self):
        from apps.clubs.models import Membership

        return get_object_or_404(
            Membership.objects.select_related("club", "student", "role"),
            pk=self.kwargs["membership_id"],
        )

    def patch(self, request, membership_id):
        membership = self.get_object()
        self._assert_can_manage(request, membership.club_id)

        serializer = MembershipRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = set_membership_role(
            membership_id=membership.pk,
            role_id=serializer.validated_data["role_id"],
        )
        return Response(MembershipSerializer(updated).data)

    def post(self, request, membership_id):
        membership = self.get_object()
        self._assert_can_manage(request, membership.club_id)

        revoked = revoke_membership(membership_id=membership.pk)
        return Response(MembershipSerializer(revoked).data)

    def _assert_can_manage(self, request, club_id):
        if not policies.has_club_permission(
            request.user, club_id, ClubPermission.MANAGE_MEMBERS
        ):
            raise PermissionDenied(
                "Tu rol en el club no incluye el permiso para gestionar miembros."
            )


class ClubDocumentsView(ClubScopedView):
    """``GET/POST /api/v1/clubs/{club_id}/documents/`` — RF-16."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, club_id):
        documents = selectors.get_club_documents(
            club_id,
            # Los privados son exclusivos de los miembros del club y de GBP.
            include_private=policies.can_see_private_documents(request.user, club_id),
        )
        return Response(
            ClubDocumentSerializer(
                documents, many=True, context={"request": request}
            ).data
        )

    def post(self, request, club_id):
        if not policies.has_club_permission(
            request.user, club_id, ClubPermission.MANAGE_DOCUMENTS
        ):
            raise PermissionDenied(
                "Tu rol en el club no incluye el permiso para subir documentos."
            )

        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document = add_club_document(club_id=club_id, **serializer.validated_data)
        return Response(
            ClubDocumentSerializer(document, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ClubDocumentDetailView(APIView):
    """``PATCH/DELETE /api/v1/club-documents/{document_id}/``."""

    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            ClubDocument.objects.select_related("club"),
            pk=self.kwargs["document_id"],
        )

    def patch(self, request, document_id):
        document = self.get_object()
        self._assert_can_manage(request, document.club_id)

        serializer = DocumentVisibilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = set_document_visibility(
            document_id=document.pk,
            is_public=serializer.validated_data["is_public"],
        )
        return Response(
            ClubDocumentSerializer(updated, context={"request": request}).data
        )

    def delete(self, request, document_id):
        document = self.get_object()
        self._assert_can_manage(request, document.club_id)

        delete_club_document(document_id=document.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _assert_can_manage(self, request, club_id):
        if not policies.has_club_permission(
            request.user, club_id, ClubPermission.MANAGE_DOCUMENTS
        ):
            raise PermissionDenied(
                "Tu rol en el club no incluye el permiso para gestionar documentos."
            )


class ClubLeaderView(ClubScopedView):
    """
    ``POST /api/v1/clubs/{club_id}/leader/assign|revoke/`` — RF-13.

    Reservado a GBP: el liderazgo lo otorga y lo retira la institución, no el
    propio club.
    """

    permission_classes = [IsAuthenticated, IsGbpAdmin]

    def post(self, request, club_id, action):
        if action == "assign":
            serializer = AssignLeaderSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            club = assign_leader(
                club_id=club_id, enrollment=serializer.validated_data["enrollment"]
            )
        else:
            club = revoke_leader(club_id=club_id)

        return Response(
            ClubInternalSerializer(
                selectors.get_club(club.pk), context={"request": request}
            ).data
        )


def _resolve_faculty(faculty_id):
    if faculty_id is None:
        return None
    return get_object_or_404(Faculty, pk=faculty_id)
