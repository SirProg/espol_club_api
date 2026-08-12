"""
Serializers de clubes — donde se materializa RN-3.

La privacidad **no** es un filtro dentro de un serializer: son dos serializers
distintos sobre la misma entidad, elegidos por ``get_serializer_class()`` según
quién pregunta. La diferencia importa. Un ``if`` dentro de
``to_representation()`` filtra datos por descuido en cuanto la entidad se anida
en otra respuesta —un club dentro de un evento, por ejemplo—, porque el contexto
del actor deja de estar disponible sin que nada avise.

Con dos clases separadas, exponer la nómina a un no miembro exige elegir
explícitamente el serializer equivocado.
"""

from rest_framework import serializers

from apps.clubs.models import Club, ClubDocument, Membership, Role


class InterestAreaBriefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class ClubDocumentSerializer(serializers.ModelSerializer):
    """
    Documento del club (RF-16).

    Qué documentos entran aquí lo decide el selector, no este serializer: un
    documento privado serializado es un documento filtrado, aunque el serializer
    sea el mismo.
    """

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ClubDocument
        fields = ["id", "title", "file_url", "is_public", "created_at"]
        read_only_fields = fields

    def get_file_url(self, document):
        request = self.context.get("request")
        url = document.file.url if document.file else None
        return request.build_absolute_uri(url) if request and url else url


class ClubPublicSerializer(serializers.ModelSerializer):
    """
    Proyección pública (V-01, V-02).

    Lo que ve el estudiante que todavía no pertenece al club: datos generales y
    **solo el contador** de miembros (RF-47). Ninguna identidad.
    """

    faculty_code = serializers.CharField(source="faculty.code", default=None)
    faculty_name = serializers.CharField(source="faculty.name", default=None)
    interest_areas = InterestAreaBriefSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    members_count = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()

    class Meta:
        model = Club
        fields = [
            "id",
            "name",
            "acronym",
            "description",
            "location",
            "faculty",
            "faculty_code",
            "faculty_name",
            "interest_areas",
            "image",
            "social_media",
            "status",
            "status_label",
            "members_count",
            "documents",
        ]
        read_only_fields = fields

    def get_members_count(self, club):
        # En listados viene anotado; en el detalle se calcula.
        annotated = getattr(club, "active_members", None)
        return annotated if annotated is not None else club.members_count

    def get_documents(self, club):
        """Solo los públicos. El selector ya los filtró; esto lo hace explícito."""
        documents = [doc for doc in club.documents.all() if doc.is_public]
        return ClubDocumentSerializer(
            documents, many=True, context=self.context
        ).data


class MembershipSerializer(serializers.ModelSerializer):
    """
    Fila de la nómina interna (V-13).

    **Nunca se anida en una respuesta pública.** Trae matrícula y correo, que es
    justamente lo que RN-3 protege.
    """

    student_id = serializers.IntegerField(source="student.id", read_only=True)
    enrollment = serializers.CharField(source="student.enrollment", read_only=True)
    full_name = serializers.CharField(source="student.get_full_name", read_only=True)
    email = serializers.EmailField(source="student.email", read_only=True)
    faculty = serializers.CharField(source="student.faculty.code", default=None)
    career = serializers.CharField(source="student.career", read_only=True)
    role_name = serializers.CharField(source="role.role_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "student_id",
            "enrollment",
            "full_name",
            "email",
            "faculty",
            "career",
            "role",
            "role_name",
            "is_leadership",
            "pao_period",
            "valid_from",
            "valid_until",
            "status",
            "status_label",
        ]
        read_only_fields = fields


class ClubInternalSerializer(ClubPublicSerializer):
    """
    Proyección interna (V-03): miembros del club y GBP.

    Añade la nómina detallada y **todos** los documentos, incluidos los
    privados.
    """

    leader = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()

    class Meta(ClubPublicSerializer.Meta):
        fields = ClubPublicSerializer.Meta.fields + [
            "leader_enrollment",
            "leader",
            "members",
        ]
        read_only_fields = fields

    def get_leader(self, club):
        if club.leader_id is None:
            return None
        return {
            "id": club.leader.id,
            "enrollment": club.leader.enrollment,
            "full_name": club.leader.get_full_name(),
            "email": club.leader.email,
        }

    def get_members(self, club):
        from apps.clubs.selectors import get_club_members

        return MembershipSerializer(
            get_club_members(club.pk), many=True, context=self.context
        ).data

    def get_documents(self, club):
        return ClubDocumentSerializer(
            club.documents.all(), many=True, context=self.context
        ).data


class RoleSerializer(serializers.ModelSerializer):
    granted_permissions = serializers.ListField(read_only=True)
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id",
            "club",
            "role_name",
            "is_default",
            "is_leadership",
            "is_active",
            "permissions",
            "granted_permissions",
            "members_count",
        ]
        read_only_fields = ["id", "club", "is_default", "granted_permissions"]

    def get_members_count(self, role):
        annotated = getattr(role, "active_members", None)
        if annotated is not None:
            return annotated
        return role.memberships.filter(status=Membership.Status.ACTIVE).count()


class RoleWriteSerializer(serializers.Serializer):
    """F-10 — alta y edición de roles personalizados."""

    role_name = serializers.CharField(max_length=80, required=False)
    is_leadership = serializers.BooleanField(required=False)
    permissions = serializers.DictField(child=serializers.BooleanField(), required=False)


class ClubWriteSerializer(serializers.Serializer):
    """F-09 / F-17 — datos del club."""

    name = serializers.CharField(max_length=150, required=False)
    acronym = serializers.CharField(max_length=30, required=False)
    description = serializers.CharField(required=False)
    location = serializers.CharField(max_length=120, required=False)
    faculty_id = serializers.IntegerField(required=False, allow_null=True)
    interest_area_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
    image = serializers.CharField(max_length=255, required=False, allow_blank=True)
    social_media = serializers.ListField(child=serializers.DictField(), required=False)


class ClubCreateSerializer(ClubWriteSerializer):
    """
    F-17 — alta de club por GBP (RF-11, RF-14).

    Aquí los campos sí son obligatorios: un club nace completo o no nace.
    """

    name = serializers.CharField(max_length=150)
    acronym = serializers.CharField(max_length=30)
    description = serializers.CharField()
    location = serializers.CharField(max_length=120)
    leader_enrollment = serializers.CharField(max_length=20)
    interest_area_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )


class MembershipRoleSerializer(serializers.Serializer):
    role_id = serializers.IntegerField()


class RenewRosterSerializer(serializers.Serializer):
    """F-15 — renovación de nómina."""

    membership_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )
    pao_period = serializers.CharField(required=False, allow_null=True)


class AssignLeaderSerializer(serializers.Serializer):
    enrollment = serializers.CharField(max_length=20)


class DocumentUploadSerializer(serializers.Serializer):
    """F-09 — carga de documento (RNF-08: solo PDF)."""

    title = serializers.CharField(max_length=150)
    file = serializers.FileField()
    is_public = serializers.BooleanField(default=False)


class DocumentVisibilitySerializer(serializers.Serializer):
    is_public = serializers.BooleanField()
