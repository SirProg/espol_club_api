"""Comandos sobre el club y sus documentos (CU-CL1..CL5)."""

from django.core.exceptions import ValidationError

from apps.clubs.models import Club, ClubDocument, Role
from apps.clubs.permissions import DEFAULT_ROLES
from core.events import emit
from core.exceptions import BusinessRuleViolation
from core.services import CLEAN_WITHOUT_UNIQUENESS, command


def create_default_roles(club):
    """
    RF-06: todo club nace con sus cuatro roles.

    Es idempotente por el UniqueConstraint (club, role_name), así que reejecutar
    el alta sobre un club existente no duplica roles.
    """
    created = []
    for spec in DEFAULT_ROLES:
        role, was_created = Role.objects.get_or_create(
            club=club,
            role_name=spec["role_name"],
            defaults={
                "is_default": True,
                "is_leadership": spec["is_leadership"],
                "permissions": spec["permissions"],
            },
        )
        if was_created:
            created.append(role)
    return created


@command
def create_club(
    *,
    name,
    acronym,
    description,
    location,
    leader_enrollment,
    faculty=None,
    interest_area_ids=(),
    image="",
    social_media=None,
):
    """
    CU-CL1 — alta de club por GBP (RF-11, RF-14, RF-15).

    Transiciones C1 o C2 según exista o no una cuenta con esa matrícula. En
    ambos casos el club nace con sus cuatro roles.
    """
    # Import local: 'leadership' importa de este módulo para crear los roles por
    # defecto, así que importarlo arriba cerraría un ciclo entre los dos.
    from apps.clubs.services.leadership import assign_leader

    if not interest_area_ids:
        raise BusinessRuleViolation(
            "El club debe declarar al menos un área de interés.",
            code="missing_interest_areas",
            field="interest_areas",
        )

    club = Club(
        name=name.strip(),
        acronym=acronym.strip(),
        description=description.strip(),
        location=location.strip(),
        faculty=faculty,
        image=image,
        social_media=social_media or [],
        leader_enrollment=(leader_enrollment or "").strip().upper(),
        # Nace sin líder resuelto; assign_leader decide si pasa a Active.
        status=Club.Status.PENDING_LEADER,
    )
    club.full_clean(exclude=["leader"], **CLEAN_WITHOUT_UNIQUENESS)
    club.save()
    club.interest_areas.set(interest_area_ids)

    create_default_roles(club)
    emit("club.created", club=club)

    if club.leader_enrollment:
        # C1 si la matrícula tiene cuenta, C2 si no: assign_leader distingue.
        assign_leader(club_id=club.pk, enrollment=club.leader_enrollment)
        club.refresh_from_db()

    return club


@command
def update_club(
    *,
    club_id,
    name=None,
    acronym=None,
    description=None,
    location=None,
    faculty=...,
    interest_area_ids=None,
    image=None,
    social_media=None,
):
    """CU-CL2 — edición de los datos del club (RF-14)."""
    club = Club.objects.get(pk=club_id)
    _assert_writable(club)

    if name is not None:
        club.name = name.strip()
    if acronym is not None:
        club.acronym = acronym.strip()
    if description is not None:
        club.description = description.strip()
    if location is not None:
        club.location = location.strip()
    if faculty is not ...:
        club.faculty = faculty
    if image is not None:
        club.image = image
    if social_media is not None:
        club.social_media = social_media

    club.full_clean(exclude=["leader"], **CLEAN_WITHOUT_UNIQUENESS)
    club.save()

    if interest_area_ids is not None:
        if not interest_area_ids:
            raise BusinessRuleViolation(
                "El club debe conservar al menos un área de interés.",
                code="missing_interest_areas",
                field="interest_areas",
            )
        club.interest_areas.set(interest_area_ids)

    return club


@command
def add_club_document(*, club_id, title, file, is_public=False):
    """CU-CL3 — carga de un documento del club (RNF-08: solo PDF)."""
    club = Club.objects.get(pk=club_id)
    _assert_writable(club)

    document = ClubDocument(
        club=club, title=title.strip(), file=file, is_public=is_public
    )
    document.full_clean(**CLEAN_WITHOUT_UNIQUENESS)
    document.save()
    return document


@command
def set_document_visibility(*, document_id, is_public):
    """CU-CL4 — alterna público/privado (RF-16)."""
    document = ClubDocument.objects.select_related("club").get(pk=document_id)
    _assert_writable(document.club)

    document.is_public = bool(is_public)
    document.save(update_fields=["is_public", "updated_at"])
    return document


@command
def delete_club_document(*, document_id):
    """
    CU-CL5 — eliminación de un documento.

    Es de los pocos borrados físicos que el sistema admite (P-4): un documento
    no tiene descendencia que quede huérfana ni evidencia que preservar.
    """
    document = ClubDocument.objects.select_related("club").get(pk=document_id)
    _assert_writable(document.club)
    document.delete()


def _assert_writable(club):
    """
    Invariante I-19: un club sin líder está en solo lectura (RF-13).

    Se comprueba en el servicio además de en la policy porque los comandos
    también se invocan desde el admin y desde management commands, que no pasan
    por las clases de permiso de la API.
    """
    if club.is_read_only:
        raise BusinessRuleViolation(
            "El club está sin líder asignado y permanece en solo lectura hasta "
            "que GBP designe uno.",
            code="club_read_only",
        )
