"""
Comandos sobre los formularios dinámicos (CU-FO1..FO6).

La regla que gobierna esta app es una sola: **un formulario con respuestas no se
edita, se versiona** (RF-24, decisión D-03). Todo lo demás se deriva de ahí.
"""

from django.db.models import Max, Q

from apps.clubs.models import Club
from apps.dynamicforms.models import Form
from apps.dynamicforms.responses import form_has_responses, response_breakdown
from apps.dynamicforms.schema import validate_responses
from core.events import emit
from core.exceptions import BusinessRuleViolation, StateTransitionError
from core.services import CLEAN_WITHOUT_UNIQUENESS, command


@command
def create_form(*, club_id, form_type, title, fields):
    """
    CU-FO1 — publica la primera versión de un formulario (RF-22).

    Si ya existe una versión vigente de ese tipo en el club, se desactiva: solo
    una está en circulación a la vez, y es la que la app móvil renderiza.
    """
    club = Club.objects.get(pk=club_id)
    _assert_writable(club)

    form = Form(
        club=club,
        form_type=form_type,
        title=title.strip(),
        fields=fields,
        version=1,
        is_active=True,
    )
    form.full_clean(**CLEAN_WITHOUT_UNIQUENESS)
    form.save()

    if form_type == Form.FormType.MEMBERSHIP:
        _deactivate_other_membership_forms(club, keep=form)

    emit("form.published", form=form)
    return form


@command
def update_form(*, form_id, title=None, fields=None):
    """
    CU-FO2 — edición en sitio, **solo si nadie ha respondido todavía**.

    Con respuestas, la operación se rechaza con 409 y el cliente debe crear una
    versión nueva. Editar en sitio dejaría respuestas apuntando a preguntas que
    ya no son las que se contestaron: el histórico mentiría.
    """
    form = Form.objects.select_for_update().select_related("club").get(pk=form_id)
    _assert_writable(form.club)

    if form_has_responses(form):
        raise StateTransitionError(
            "Este formulario ya tiene respuestas y no puede modificarse. "
            "Crea una versión nueva para cambiar las preguntas.",
            code="form_has_responses",
        )

    if title is not None:
        form.title = title.strip()
    if fields is not None:
        form.fields = fields

    form.full_clean(**CLEAN_WITHOUT_UNIQUENESS)
    form.save()
    return form


@command
def create_new_version(*, form_id, title=None, fields=None):
    """
    CU-FO1 (versionado) — publica la versión siguiente de la familia.

    La versión anterior queda desactivada pero **no se borra**: las respuestas
    ya enviadas la siguen referenciando y deben poder leerse contra el esquema
    con el que se llenaron.
    """
    previous = Form.objects.select_for_update().select_related("club").get(pk=form_id)
    _assert_writable(previous.club)

    root_id = previous.family_id
    # La versión se cuenta sobre toda la familia, no sobre la fila de origen:
    # versionar dos veces desde la v1 debe dar v2 y v3, no v2 y v2.
    next_version = (
        Form.objects.filter(Q(pk=root_id) | Q(root_id=root_id)).aggregate(
            Max("version")
        )["version__max"]
        or previous.version
    ) + 1

    new_version = Form(
        club=previous.club,
        form_type=previous.form_type,
        title=(title or previous.title).strip(),
        fields=fields if fields is not None else previous.fields,
        version=next_version,
        is_active=True,
        root_id=root_id,
    )
    new_version.full_clean(**CLEAN_WITHOUT_UNIQUENESS)
    new_version.save()

    previous.is_active = False
    previous.save(update_fields=["is_active", "updated_at"])

    emit("form.published", form=new_version, replaces=previous)
    return new_version


@command
def deactivate_form(*, form_id):
    """
    CU-FO3 — retira el formulario de circulación.

    Para un formulario de membresía equivale a cerrar las postulaciones; para
    uno de evento, a cerrar el registro.
    """
    form = Form.objects.select_related("club").get(pk=form_id)
    _assert_writable(form.club)

    form.is_active = False
    form.save(update_fields=["is_active", "updated_at"])
    return form


@command
def activate_form(*, form_id):
    """Vuelve a poner en circulación una versión, desactivando la que estuviera."""
    form = Form.objects.select_related("club").get(pk=form_id)
    _assert_writable(form.club)

    if form.form_type == Form.FormType.MEMBERSHIP:
        _deactivate_other_membership_forms(form.club, keep=form)

    form.is_active = True
    form.save(update_fields=["is_active", "updated_at"])
    return form


@command
def delete_form(*, form_id):
    """
    CU-FO4 — borrado físico, admitido solo sin respuestas.

    Es una de las pocas excepciones a P-4 (nada se borra): un formulario sin
    respuestas no es evidencia de nada.
    """
    form = Form.objects.select_related("club").get(pk=form_id)
    _assert_writable(form.club)

    if form_has_responses(form):
        raise BusinessRuleViolation(
            "Este formulario tiene respuestas asociadas y no puede eliminarse. "
            "Desactívalo para retirarlo de circulación.",
            code="form_has_responses",
        )
    if form.versions.exists():
        raise BusinessRuleViolation(
            "Este formulario es el origen de otras versiones y no puede "
            "eliminarse.",
            code="form_is_version_root",
        )

    form.delete()


def validate_submission(form, responses):
    """
    CU-FO6 — puerta de entrada de toda respuesta al sistema.

    No es un comando: no muta nada. La usan la postulación (Etapa 6) y la
    inscripción a evento (Etapa 7) **antes** de crear su registro, y devuelve
    las respuestas normalizadas tal como deben almacenarse.
    """
    if not form.is_active:
        raise BusinessRuleViolation(
            "Este formulario ya no está disponible.", code="form_inactive"
        )
    return validate_responses(form.fields, responses)


def describe_response_sources(form):
    """Desglose de quién generó las respuestas. Alimenta el mensaje del 409."""
    return response_breakdown(form)


def _deactivate_other_membership_forms(club, *, keep):
    """
    Un club tiene un solo formulario de membresía vigente.

    A diferencia de los eventos —donde cada evento tiene el suyo—, la
    postulación al club es una sola puerta: dos formularios vigentes dejarían
    ambiguo cuál debe renderizar la app (RF-25).
    """
    Form.objects.filter(
        club=club, form_type=Form.FormType.MEMBERSHIP, is_active=True
    ).exclude(pk=keep.pk).update(is_active=False)


def _assert_writable(club):
    if club.is_read_only:
        raise BusinessRuleViolation(
            "El club está sin líder asignado y permanece en solo lectura.",
            code="club_read_only",
        )
