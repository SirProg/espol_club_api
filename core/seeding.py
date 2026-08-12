"""
Utilidades compartidas por los comandos de sembrado.

Existen dos conjuntos de datos que conviven:

* ``seed_demo_data`` reproduce MASTER §17 — seis cuentas y dos clubes, pensado
  para **probar reglas de negocio**. Sus conteos están fijados en los tests.
* ``seed_espol_data`` puebla con los clubes reales de ESPOL para **desarrollar
  interfaces**: catálogo filtrable, eventos con métricas, histórico por período.

Cada uno borra lo suyo, pero el **orden de borrado** es común y delicado: va de
las hojas hacia la raíz siguiendo los ``on_delete=PROTECT`` del dominio.
Equivocarlo produce un ``ProtectedError`` que no dice mucho, y duplicar la
secuencia en dos comandos garantiza que uno de los dos se quede atrás cuando
aparezca una entidad nueva.
"""

from django.contrib.auth import get_user_model
from django.db import transaction

Student = get_user_model()


@transaction.atomic
def purge_clubs(acronyms, *, enrollments=(), pao_periods=()):
    """
    Borra clubes con todo lo que cuelga de ellos, y opcionalmente cuentas y
    períodos.

    El orden es de las hojas a la raíz:

    1. Asistencias → inscripciones → staff → eventos
    2. Solicitudes y trámites (protegen a los formularios)
    3. Formularios
    4. Notificaciones, membresías, documentos, roles
    5. Clubes
    6. Cuentas y períodos

    Si algún día se añade una entidad que cuelgue de un club y no se incluya
    aquí, esto falla con ``ProtectedError`` en vez de borrar a medias — que es
    justo lo que debe pasar.
    """
    # Imports locales: 'core' no conoce el dominio por diseño. Aquí se hace la
    # excepción porque limpiar exige nombrar todo lo que puede colgar de un club.
    from apps.academic.models import PaoPeriod
    from apps.applications.models import MembershipApplication
    from apps.clubs.models import Club, ClubDocument, Membership, Role
    from apps.dynamicforms.models import Form
    from apps.events.models import (
        Event,
        EventAttendance,
        EventRegistration,
        EventStaff,
    )
    from apps.gbp.models import GbpDocumentProcess
    from apps.notifications.models import Notification

    clubs = Club.objects.filter(acronym__in=acronyms)
    events = Event.objects.filter(club__in=clubs)

    EventAttendance.objects.filter(event__in=events).delete()
    EventRegistration.objects.filter(event__in=events).delete()
    EventStaff.objects.filter(event__in=events).delete()
    events.delete()

    MembershipApplication.objects.filter(club__in=clubs).delete()
    GbpDocumentProcess.objects.filter(club__in=clubs).delete()
    Form.objects.filter(club__in=clubs).delete()

    Notification.objects.filter(club__in=clubs).delete()
    Membership.objects.filter(club__in=clubs).delete()
    ClubDocument.objects.filter(club__in=clubs).delete()
    Role.objects.filter(club__in=clubs).delete()
    clubs.delete()

    if enrollments:
        students = Student.objects.filter(enrollment__in=enrollments)
        # Las notificaciones apuntan al usuario con CASCADE, pero se borran
        # explícitamente para no depender de ese detalle.
        Notification.objects.filter(user__in=students).delete()
        students.delete()

    if pao_periods:
        # Solo se borran los períodos que ya no usa nadie. Los dos conjuntos de
        # sembrado comparten 2025-II y 2026-I, y las membresías y trámites los
        # referencian con PROTECT: intentar borrarlos a ciegas hace fallar el
        # comando entero con un ProtectedError de cientos de líneas, cuando lo
        # correcto es simplemente conservarlos.
        for period in PaoPeriod.objects.filter(pao_period__in=pao_periods):
            if period.memberships.exists() or period.gbp_processes.exists():
                continue
            period.delete()


def ensure_pao_periods(specs):
    """
    Crea los períodos que falten y reutiliza los que ya existan.

    Hace falta porque los dos conjuntos de sembrado comparten 2025-II y 2026-I.
    Llamar a ``create_pao`` sobre un período existente **no** falla con un error
    de duplicado como cabría esperar: ``PaoPeriod`` tiene llave primaria natural,
    así que Django resuelve el ``save()`` como un UPDATE, y en un UPDATE el
    campo ``auto_now_add`` no se rellena. El resultado es un
    ``created_at cannot be null`` que no dice nada sobre la causa real.
    """
    from apps.academic.models import PaoPeriod
    from apps.academic.services import activate_pao, create_pao

    periods = {}
    for spec in specs:
        existing = PaoPeriod.objects.filter(pk=spec["pao_period"]).first()
        if existing:
            if spec.get("activate") and not existing.is_active:
                activate_pao(existing.pk)
                existing.refresh_from_db()
            periods[spec["pao_period"]] = existing
            continue

        periods[spec["pao_period"]] = create_pao(
            pao_period=spec["pao_period"],
            start_date=spec["start_date"],
            end_date=spec["end_date"],
            activate=spec.get("activate", False),
        )
    return periods


def confirm_destructive(command, message, *, noinput):
    """
    Pide confirmación antes de un borrado.

    ``--noinput`` la salta, para poder automatizar. Sin ese flag, escribir
    cualquier cosa distinta de 'si' cancela: no vale un Enter distraído.
    """
    if noinput:
        return

    command.stdout.write(command.style.WARNING(message))
    answer = input("Escribe 'si' para continuar: ")
    if answer.strip().lower() not in {"si", "sí"}:
        from django.core.management.base import CommandError

        raise CommandError("Cancelado.")
