"""
Puebla la API con los clubes reales de ESPOL.

**Para qué sirve, frente a ``seed_demo_data``.** Aquel reproduce MASTER §17 —seis
cuentas y dos clubes— y existe para probar reglas de negocio; sus conteos están
fijados en los tests. Este otro existe para **desarrollar interfaces**: con dos
clubes no se prueba un catálogo paginado, ni un filtro por facultad, ni un
histórico por período. Los dos conjuntos conviven.

**De dónde salen los datos.** Los clubes, sus descripciones, los tipos de
trámite y el calendario son reales, tomados del portal de la Unidad de Bienestar
Politécnico (``oe.espol.edu.ec``). Ver ``core/espol_data.py``, donde cada bloque
declara su procedencia. Las **personas son ficticias** y quedan marcadas como
tales en su perfil.

**Cómo se siembra.** A través de los servicios del dominio, nunca escribiendo
modelos a mano. El motivo está explicado en ``seed_demo_data``: dos campos
derivados se calculan en ``save()``, y saltárselos produce un conjunto que
contradice las reglas que debería demostrar. Como efecto secundario, este
comando es una prueba de extremo a extremo: si una regla está rota, falla.

**Las notificaciones no se crean aquí.** Nacen de los eventos de dominio al
ejecutar los servicios. Que el centro de notificaciones acabe poblado es la
prueba de que el bus funciona.
"""

import datetime
import random
import unicodedata

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.academic.models import PaoPeriod
from apps.academic.services import create_pao
from apps.applications.services import (
    approve_application,
    reject_application,
    submit_application,
)
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs.models import Club, Membership, Role
from apps.clubs.services.clubs import add_club_document, create_club
from apps.clubs.services.memberships import (
    create_membership,
    freeze_expired_memberships,
)
from apps.clubs.services.roles import create_role
from apps.dynamicforms.models import Form
from apps.dynamicforms.services import create_form, create_new_version
from apps.events.models import Event
from apps.events.services.attendance import register_scan
from apps.events.services.events import create_event, set_event_staff
from apps.events.services.registration import (
    expire_qr_tokens,
    mark_no_shows,
    register_for_event,
)
from apps.gbp.models import GbpDocumentProcess
from apps.gbp.services import resolve_process, submit_process, take_process
from core import espol_data
from core.exceptions import DomainError
from core.management.commands.seed_demo_data import build_minimal_pdf
from core.seeding import confirm_destructive, ensure_pao_periods, purge_clubs

Student = get_user_model()


def slugify_name(text):
    """'María Cevallos' -> 'mcevallos'. Sin tildes ni espacios, para el correo."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode()
    return ascii_only.lower().replace(" ", "")


class Command(BaseCommand):
    help = (
        "Puebla la API con los clubes reales de ESPOL, para desarrollar los "
        "clientes web y móvil contra datos que se parecen a los de producción."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Borra este conjunto antes de regenerarlo. DESTRUCTIVO. No "
            "toca los datos de seed_demo_data.",
        )
        parser.add_argument(
            "--noinput", action="store_true", help="No pide confirmación."
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=2026,
            help="Semilla de aleatoriedad. Con la misma semilla, el conjunto "
            "generado es idéntico.",
        )

    def handle(self, *args, **options):
        # A diferencia de seed_demo_data, este comando SÍ puede correr en
        # producción: es lo que consumirán el panel React y la app React Native.
        # Por eso avisa en vez de bloquear, y el borrado exige confirmación.
        if not settings.DEBUG:
            self.stdout.write(
                self.style.WARNING(
                    "Ejecutando en un entorno con DEBUG=False. Se van a crear "
                    "cuentas de demostración con una contraseña conocida."
                )
            )

        self.random = random.Random(options["seed"])

        if options["reset"]:
            self._reset(noinput=options["noinput"])

        acronyms = [club["acronym"] for club in espol_data.CLUBS]
        if Club.objects.filter(acronym__in=acronyms).exists():
            self.stdout.write(
                self.style.WARNING(
                    "El conjunto de ESPOL ya existe. Usa --reset para regenerarlo."
                )
            )
            return

        with transaction.atomic():
            paos = self._seed_paos()
            students = self._seed_students()
            clubs = self._seed_clubs(students)
            forms = self._seed_forms(clubs)
            self._seed_custom_roles(clubs)
            self._seed_rosters(clubs, students, paos)
            self._seed_applications(clubs, students, forms)
            events = self._seed_events(clubs, forms)
            self._seed_registrations_and_attendance(events, clubs, students)
            self._seed_documents(clubs)
            self._seed_gbp_processes(clubs)

        self._report(clubs, students)

    # -- Reset ------------------------------------------------------------

    def _reset(self, *, noinput):
        acronyms = [club["acronym"] for club in espol_data.CLUBS]
        enrollments = list(
            Student.objects.filter(
                enrollment__startswith=espol_data.DEMO_ENROLLMENT_PREFIX
            ).values_list("enrollment", flat=True)
        )

        confirm_destructive(
            self,
            f"Se eliminarán {len(acronyms)} clubes de ESPOL con todo su "
            f"contenido y {len(enrollments)} cuentas de demostración. "
            "Los datos de seed_demo_data NO se tocan.",
            noinput=noinput,
        )

        purge_clubs(
            acronyms,
            enrollments=enrollments,
            # Los períodos se conservan: seed_demo_data comparte 2025-II y
            # 2026-I, y borrarlos rompería el otro conjunto.
            pao_periods=(),
        )
        self.stdout.write(self.style.SUCCESS("Conjunto de ESPOL eliminado."))

    # -- Períodos ---------------------------------------------------------

    def _seed_paos(self):
        # Reutiliza los que ya existan: seed_demo_data comparte 2025-II y 2026-I.
        paos = ensure_pao_periods(espol_data.PAO_PERIODS)
        self.stdout.write(f"  Períodos académicos: {len(paos)}")
        return paos

    # -- Personas ---------------------------------------------------------

    def _seed_students(self):
        """
        Genera las cuentas de demostración.

        Se producen más de las que se usan como miembros: hacen falta
        postulantes que **no** pertenezcan a ningún club para que la pantalla de
        postulación tenga con quién probarse.
        """
        faculties = {f.code: f for f in Faculty.objects.all()}
        students = []
        used_emails = set(Student.objects.values_list("email", flat=True))

        total = 70
        for index in range(total):
            first = self.random.choice(espol_data.FIRST_NAMES)
            last = self.random.choice(espol_data.LAST_NAMES)
            second_last = self.random.choice(espol_data.LAST_NAMES)
            faculty_code = self.random.choice(list(espol_data.CAREERS_BY_FACULTY))

            enrollment = (
                f"{espol_data.DEMO_ENROLLMENT_PREFIX}"
                f"{espol_data.DEMO_ENROLLMENT_START + index}"
            )
            base_email = f"{first[0]}{slugify_name(last)}"
            email = f"{base_email}@espol.edu.ec"
            suffix = 1
            while email in used_emails:
                suffix += 1
                email = f"{base_email}{suffix}@espol.edu.ec"
            used_emails.add(email)

            student = Student.objects.create_user(
                enrollment=enrollment,
                email=email,
                password=espol_data.DEMO_PASSWORD,
                first_name=first,
                last_name=f"{last} {second_last}",
                birth_date=datetime.date(
                    self.random.randint(2000, 2006),
                    self.random.randint(1, 12),
                    self.random.randint(1, 28),
                ),
                faculty=faculties[faculty_code],
                career=self.random.choice(
                    espol_data.CAREERS_BY_FACULTY[faculty_code]
                ),
                semester=self.random.randint(1, 10),
                description=espol_data.DEMO_PROFILE_NOTE,
                skills=self.random.sample(espol_data.SKILLS_POOL, k=3),
                is_verified=True,
            )
            students.append(student)

        self.stdout.write(f"  Estudiantes de demostración: {len(students)}")
        return students

    # -- Clubes -----------------------------------------------------------

    def _seed_clubs(self, students):
        """
        Da de alta los clubes.

        Cada líder se toma de una lista que se va consumiendo: RN-1 impide que
        una persona lidere dos clubes, así que reutilizar a alguien haría fallar
        el alta —y con razón—.
        """
        faculties = {f.code: f for f in Faculty.objects.all()}
        areas = {a.name: a for a in InterestArea.objects.all()}
        clubs = {}
        leader_pool = list(students)

        for spec in espol_data.CLUBS:
            if spec["size"] == "sin_lider":
                # Matrícula comprometida por GBP que todavía no tiene cuenta:
                # el club queda 'Pending Leader' (RF-12, decisión D-01).
                leader_enrollment = "202099777"
            else:
                leader = leader_pool.pop(0)
                leader_enrollment = leader.enrollment

            club = create_club(
                name=spec["name"],
                acronym=spec["acronym"],
                description=spec["description"],
                location=spec["location"],
                leader_enrollment=leader_enrollment,
                faculty=faculties[spec["faculty"]],
                interest_area_ids=[areas[a].id for a in spec["areas"]],
            )
            clubs[spec["acronym"]] = {"club": club, "spec": spec}

        activos = sum(1 for c in clubs.values() if c["club"].is_active)
        self.stdout.write(
            f"  Clubes: {len(clubs)} ({activos} activos, "
            f"{len(clubs) - activos} sin líder)"
        )
        return clubs

    def _seed_custom_roles(self, clubs):
        """RF-07: que el panel de roles muestre algo más que los 4 por defecto."""
        created = 0
        for entry in clubs.values():
            if entry["club"].is_read_only:
                continue
            for role_name, permissions in self.random.sample(
                espol_data.CUSTOM_ROLES, k=self.random.randint(1, 3)
            ):
                create_role(
                    club_id=entry["club"].pk,
                    role_name=role_name,
                    permissions=permissions,
                )
                created += 1
        self.stdout.write(f"  Roles personalizados: {created}")

    # -- Formularios ------------------------------------------------------

    def _seed_forms(self, clubs):
        """
        Un formulario de membresía por club y uno de evento.

        A uno se le crea una **versión nueva** para que RF-24 sea visible desde
        el cliente: un formulario con respuestas no se edita, se versiona.
        """
        forms = {}
        for acronym, entry in clubs.items():
            if entry["club"].is_read_only:
                continue

            membership_form = create_form(
                club_id=entry["club"].pk,
                form_type=Form.FormType.MEMBERSHIP,
                title=f"Postulación a {acronym}",
                fields=espol_data.MEMBERSHIP_FORM_FIELDS,
            )
            event_form = create_form(
                club_id=entry["club"].pk,
                form_type=Form.FormType.EVENT,
                title=f"Registro a eventos de {acronym}",
                fields=espol_data.EVENT_FORM_FIELDS,
            )
            forms[acronym] = {"membership": membership_form, "event": event_form}

        self.stdout.write(f"  Formularios: {len(forms) * 2}")
        return forms

    # -- Nóminas ----------------------------------------------------------

    def _seed_rosters(self, clubs, students, paos):
        """
        Puebla las nóminas con tamaños variables.

        Un catálogo donde todos los clubes tienen el mismo número de miembros no
        ejercita nada: ni el orden, ni los contadores, ni las diferencias que el
        cliente debe saber mostrar.

        Se dejan los primeros estudiantes fuera de toda nómina, a propósito: son
        los que servirán para probar la postulación.
        """
        candidates = students[len(clubs) :]
        reserved = candidates[:12]  # nunca serán miembros: postulantes puros
        pool = candidates[12:]

        total = 0
        for entry in clubs.values():
            if entry["club"].is_read_only:
                continue

            low, high = espol_data.ROSTER_SIZES[entry["spec"]["size"]]
            size = self.random.randint(low, high)
            members = self.random.sample(pool, k=min(size, len(pool)))

            roles = list(
                Role.objects.filter(club=entry["club"], is_leadership=False)
            )
            for student in members:
                try:
                    create_membership(
                        student=student,
                        club=entry["club"],
                        role=self.random.choice(roles),
                        origin=Membership.Origin.SEED,
                    )
                    total += 1
                except DomainError:
                    # Ya era miembro de este club: el muestreo puede repetir.
                    continue

        self.stdout.write(f"  Membresías del período vigente: {total}")
        self._reserved_applicants = reserved
        self._seed_historical_rosters(clubs, pool, paos)

    def _seed_historical_rosters(self, clubs, pool, paos):
        """
        Nóminas congeladas de un período anterior.

        Sin esto el histórico (RF-49) devuelve vacío y la pantalla de renovación
        de nómina (RF-21) no tiene nada que renovar.
        """
        previous = paos[espol_data.PREVIOUS_PAO]
        total = 0

        for entry in list(clubs.values())[:8]:
            if entry["club"].is_read_only:
                continue
            role = Role.objects.filter(
                club=entry["club"], role_name="Miembro"
            ).first()
            for student in self.random.sample(pool, k=self.random.randint(5, 12)):
                try:
                    create_membership(
                        student=student,
                        club=entry["club"],
                        role=role,
                        pao_period=previous,
                        origin=Membership.Origin.SEED,
                    )
                    total += 1
                except DomainError:
                    continue

        # Se congelan ejecutando la transición real (M2), no escribiendo el
        # estado a mano: el dato semilla es el resultado de la regla.
        # notify=False porque nadie debe recibir hoy un aviso de 2025.
        frozen = freeze_expired_memberships(
            today=previous.end_date + datetime.timedelta(days=1), notify=False
        )
        self.stdout.write(
            f"  Membresías históricas: {total} ({frozen} congeladas)"
        )

    # -- Solicitudes ------------------------------------------------------

    def _seed_applications(self, clubs, students, forms):
        """
        Solicitudes en los tres estados.

        La bandeja del líder necesita pendientes que resolver; el historial del
        estudiante, resueltas que mostrar. Y un rechazo con justificación deja
        ver RF-29: se puede volver a postular de inmediato.
        """
        applicants = self._reserved_applicants
        pending = approved = rejected = 0

        active_clubs = [e for e in clubs.values() if not e["club"].is_read_only]

        for index, student in enumerate(applicants):
            for entry in self.random.sample(active_clubs, k=3):
                acronym = entry["spec"]["acronym"]
                if acronym not in forms:
                    continue
                try:
                    application = submit_application(
                        student=student,
                        club_id=entry["club"].pk,
                        responses={
                            "motivacion": (
                                f"Me interesa participar en {acronym} para "
                                "aplicar lo que aprendo en clase y conocer "
                                "gente con los mismos intereses."
                            ),
                            "experiencia": self.random.choice(
                                ["Ninguna", "Principiante", "Intermedio"]
                            ),
                            "disponibilidad": self.random.randint(2, 10),
                            "intereses": self.random.sample(
                                ["Proyectos", "Capacitación", "Competencias"], k=2
                            ),
                        },
                    )
                except DomainError:
                    continue

                leader = entry["club"].leader
                decision = index % 3
                if decision == 0:
                    pending += 1  # se queda pendiente
                elif decision == 1:
                    approve_application(
                        application_id=application.pk, resolved_by=leader
                    )
                    approved += 1
                else:
                    reject_application(
                        application_id=application.pk,
                        resolved_by=leader,
                        feedback=self.random.choice(
                            espol_data.APPLICATION_REJECTION_FEEDBACK
                        ),
                    )
                    rejected += 1

        self.stdout.write(
            f"  Solicitudes: {pending} pendientes, {approved} aprobadas, "
            f"{rejected} rechazadas"
        )

    # -- Eventos ----------------------------------------------------------

    def _seed_events(self, clubs, forms):
        """
        Eventos repartidos en el tiempo.

        Hacen falta los tres momentos: pasados con asistencia registrada para
        que las métricas de RF-38 tengan valores, en curso para que el escaneo
        sea posible, y futuros con registro abierto para que el cliente pueda
        inscribirse de verdad.

        **Todos nacen en el futuro**, incluidos los que acabarán siendo
        pasados. No es un rodeo: ``can_register`` rechaza —con razón— inscribirse
        a un evento terminado, así que crearlo ya vencido haría imposible
        poblarlo. Se sigue el orden real de los hechos: primero se anuncia el
        evento, luego la gente se inscribe, y solo después el evento ocurre.
        El desplazamiento en el tiempo lo hace ``_shift_past_events``.
        """
        now = timezone.localtime()
        events = []

        for acronym, entry in clubs.items():
            if entry["club"].is_read_only:
                continue

            category = entry["spec"]["category"]
            templates = espol_data.EVENT_TEMPLATES[category]
            topics = espol_data.EVENT_TOPICS.get(acronym, ["actividades del club"])
            event_form = forms[acronym]["event"]

            # (desplazamiento en días, visibilidad) — el pasado, el presente y
            # el futuro, más uno solo para miembros.
            plan = [
                (-45, Event.Visibility.PUBLIC),
                (-20, Event.Visibility.PUBLIC),
                (0, Event.Visibility.PUBLIC),
                (12, Event.Visibility.PUBLIC),
                (25, Event.Visibility.MEMBERS_ONLY),
            ]

            for offset, visibility in plan:
                template, place, mode = self.random.choice(templates)
                topic = self.random.choice(topics)
                # Se crea siempre en el futuro; el offset se aplica después.
                days_ahead = offset if offset > 0 else abs(offset) + 3
                start = (now + datetime.timedelta(days=days_ahead)).replace(
                    hour=self.random.choice([9, 11, 14, 16]),
                    minute=0,
                    second=0,
                    microsecond=0,
                )
                event = create_event(
                    club_id=entry["club"].pk,
                    event_name=template.format(tema=topic),
                    mode=mode,
                    planned_date=start.date(),
                    planned_hour=start.time(),
                    end_datetime=start + datetime.timedelta(hours=3),
                    planned_place=place.format(aula=self.random.randint(1, 30)),
                    description=(
                        f"Actividad organizada por {acronym} dentro del "
                        "Programa de Apoyo a Clubes Estudiantiles de la ESPOL."
                    ),
                    visibility=visibility,
                    registration_form_id=event_form.pk,
                    registration_deadline=start - datetime.timedelta(hours=6),
                    blocked_message=(
                        "Evento exclusivo para miembros del club."
                        if visibility == Event.Visibility.MEMBERS_ONLY
                        else "El registro para este evento ya cerró."
                    ),
                    expected_participants=self.random.choice([20, 30, 50, 80]),
                )
                events.append({"event": event, "club": entry["club"], "offset": offset})

        self.stdout.write(f"  Eventos: {len(events)}")
        return events

    def _seed_registrations_and_attendance(self, events, clubs, students):
        """
        Inscripciones, desplazamiento en el tiempo y asistencias.

        Tres fases, en este orden y no en otro:

        1. **Inscribir** mientras todos los eventos siguen siendo futuros, que
           es cuando el registro está abierto.
        2. **Mover al pasado** los que deben haber ocurrido ya.
        3. **Escanear** las asistencias con ``register_scan``, es decir con la
           operación real (CU-EV9), no escribiendo el estado. Así las métricas
           de inscritos frente a asistentes salen del flujo y no de una
           afirmación.
        """
        registrations = 0
        staff_by_event = {}

        for item in events:
            event, club = item["event"], item["club"]
            members = list(
                Membership.objects.filter(
                    club=club, status=Membership.Status.ACTIVE
                ).select_related("student")
            )
            if not members:
                continue

            # RF-35: el escaneo exige estar asignado como staff de ESE evento.
            staff = members[0].student
            set_event_staff(event_id=event.pk, student_ids=[staff.pk])
            staff_by_event[event.pk] = staff

            attendees = self.random.sample(
                members, k=min(len(members), self.random.randint(4, 14))
            )
            item["registrations"] = []
            for membership in attendees:
                try:
                    registration = register_for_event(
                        student=membership.student,
                        event_id=event.pk,
                        responses={
                            "nivel": self.random.choice(
                                ["Principiante", "Intermedio", "Avanzado"]
                            ),
                            "expectativa": "Aprender y conocer al equipo del club.",
                        },
                    )
                except DomainError:
                    continue
                item["registrations"].append(registration)
                registrations += 1

        scans = self._shift_past_events_and_scan(events, staff_by_event)

        # Los procesos programados cierran el ciclo de los eventos pasados.
        expired = expire_qr_tokens()
        no_shows = mark_no_shows()

        self.stdout.write(
            f"  Inscripciones: {registrations} · asistencias escaneadas: {scans}"
        )
        self.stdout.write(
            f"  QR expirados: {expired} · marcados como ausencia: {no_shows}"
        )

    def _shift_past_events_and_scan(self, events, staff_by_event):
        """
        Mueve al pasado los eventos que ya debían haber ocurrido y registra su
        asistencia.

        El desplazamiento se hace con un ``save()`` directo a propósito: es una
        **simulación del paso del tiempo**, no una operación de negocio. No
        existe —ni debe existir— un servicio para "mover un evento al pasado".
        """
        now = timezone.localtime()
        scans = 0

        for item in events:
            if item["offset"] >= 0:
                continue

            event = item["event"]
            start = (now + datetime.timedelta(days=item["offset"])).replace(
                hour=event.planned_hour.hour, minute=0, second=0, microsecond=0
            )
            event.planned_date = start.date()
            event.planned_hour = start.time()
            event.end_datetime = start + datetime.timedelta(hours=3)
            event.registration_deadline = start - datetime.timedelta(hours=6)
            event.save()

            staff = staff_by_event.get(event.pk)
            if staff is None:
                continue

            # No todos los inscritos aparecen: si asistiera el 100%, la métrica
            # de inscritos frente a asistentes no mostraría nada.
            for registration in item.get("registrations", []):
                if self.random.random() > 0.7:
                    continue
                try:
                    register_scan(
                        qr_token=registration.qr_token,
                        staff_student=staff,
                        now=event.start_datetime + datetime.timedelta(minutes=20),
                    )
                    scans += 1
                except DomainError:
                    continue

        return scans

    # -- Documentos y trámites --------------------------------------------

    def _seed_documents(self, clubs):
        """Documentos públicos y privados, para que RF-16 se vea desde el cliente."""
        total = 0
        for acronym, entry in clubs.items():
            if entry["club"].is_read_only:
                continue
            for title, is_public in espol_data.CLUB_DOCUMENTS:
                add_club_document(
                    club_id=entry["club"].pk,
                    title=f"{title} — {acronym}",
                    file=ContentFile(
                        build_minimal_pdf(title),
                        name=f"{slugify_name(acronym)}_{slugify_name(title)}.pdf",
                    ),
                    is_public=is_public,
                )
                total += 1
        self.stdout.write(f"  Documentos de club: {total}")

    def _seed_gbp_processes(self, clubs):
        """
        Trámites en los cuatro estados de §5.5.

        El buzón de GBP necesita algo que revisar y algo ya resuelto; el club,
        ver en qué quedó lo que envió.
        """
        counts = {"Submitted": 0, "Under Review": 0, "Approved": 0, "Rejected": 0}
        gbp = Student.objects.filter(is_gbp_admin=True).first()
        if gbp is None:
            self.stdout.write(
                self.style.WARNING(
                    "  Sin administrador GBP: se omiten los trámites. "
                    "Créalo con provision_gbp_admin."
                )
            )
            return

        active = [e for e in clubs.values() if not e["club"].is_read_only]
        for index, entry in enumerate(active):
            leader = entry["club"].leader
            document_type = espol_data.GBP_DOCUMENT_TYPES[
                index % len(espol_data.GBP_DOCUMENT_TYPES)
            ]
            process = submit_process(
                club_id=entry["club"].pk,
                pao_period=espol_data.CURRENT_PAO,
                document_type=document_type,
                file=ContentFile(
                    build_minimal_pdf(document_type),
                    name=f"{slugify_name(entry['spec']['acronym'])}_tramite.pdf",
                ),
                submitted_by=leader,
            )

            stage = index % 4
            if stage == 0:
                counts["Submitted"] += 1
                continue

            take_process(process_id=process.pk, reviewer=gbp)
            if stage == 1:
                counts["Under Review"] += 1
                continue

            approved = stage == 2
            resolve_process(
                process_id=process.pk,
                reviewer=gbp,
                approved=approved,
                feedback=(
                    ""
                    if approved
                    else self.random.choice(espol_data.GBP_REJECTION_FEEDBACK)
                ),
            )
            counts["Approved" if approved else "Rejected"] += 1

        resumen = " · ".join(f"{k}: {v}" for k, v in counts.items())
        self.stdout.write(f"  Trámites GBP → {resumen}")

    # -- Reporte ----------------------------------------------------------

    def _report(self, clubs, students):
        from apps.notifications.models import Notification

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Datos de ESPOL creados."))
        self.stdout.write("")
        self.stdout.write(
            f"  Notificaciones generadas por el bus de eventos: "
            f"{Notification.objects.count()}"
        )
        self.stdout.write("")
        self.stdout.write("Cuentas para probar los clientes:")
        self.stdout.write(
            f"  Contraseña de todas: {espol_data.DEMO_PASSWORD}"
        )
        self.stdout.write("")

        for acronym, entry in list(clubs.items())[:5]:
            leader = entry["club"].leader
            if leader:
                self.stdout.write(
                    f"  Líder de {acronym:<14} {leader.enrollment}  "
                    f"{leader.get_full_name()}"
                )

        sin_club = [
            s
            for s in students
            if not Membership.objects.filter(student=s).exists()
        ][:3]
        if sin_club:
            self.stdout.write("")
            self.stdout.write("  Estudiantes sin club (para probar postulación):")
            for student in sin_club:
                self.stdout.write(
                    f"    {student.enrollment}  {student.get_full_name()}"
                )
