"""
Siembra el estado de la Fase 1 (MASTER §17) en la base de desarrollo.

**Por qué no es una fixture de ``loaddata``.**

``loaddata`` deserializa y guarda con ``Model.save_base(raw=True)``, lo que se
salta ``Model.save()``. En este esquema eso no es un detalle: dos campos
derivados se calculan justamente ahí.

* ``PaoPeriod.sequence`` — sin ``save()`` nunca se calcula, y la columna es NOT
  NULL: habría que escribir el valor a mano en el JSON.
* ``Membership.is_leadership`` — el snapshot del que depende el invariante I-09.
  Sin ``save()`` se queda en ``False``, la columna generada ``leadership_lock``
  vale NULL, y **el índice único de RN-1 deja de vigilar esa fila**.

El segundo caso es el grave: la fixture cargaría sin error y produciría un
conjunto donde una persona figura como Presidente/a de dos clubes sin que nada
lo detecte. Un dataset semilla que contradice la regla que debe demostrar es
peor que no tener dataset.

Sembrar a través de los servicios evita eso y, de paso, convierte el comando en
una prueba de extremo a extremo del dominio: si una regla de negocio está rota,
el sembrado falla.
"""

import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.academic.models import PaoPeriod
from apps.academic.services import create_pao
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs.models import Club, ClubDocument, Membership, Role
from apps.clubs.services.clubs import add_club_document, create_club
from apps.clubs.services.memberships import create_membership, freeze_expired_memberships
from apps.clubs.services.roles import create_role
from core import seed_data

Student = get_user_model()


def build_minimal_pdf(title):
    """
    Genera un PDF mínimo pero **válido**, con su tabla xref bien calculada.

    Los documentos del club pasan por ``validate_pdf_file``, así que un archivo
    de relleno con extensión .pdf serviría para cargar; se genera un PDF real
    para que además se pueda abrir y el dato semilla no sea una mentira.
    """
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>",
    ]

    header = b"%PDF-1.4\n"
    body = b""
    offsets = []
    for index, content in enumerate(objects, start=1):
        offsets.append(len(header) + len(body))
        body += b"%d 0 obj\n" % index + content + b"\nendobj\n"

    xref_position = len(header) + len(body)
    xref = b"xref\n0 %d\n" % (len(objects) + 1)
    xref += b"0000000000 65535 f \n"
    for offset in offsets:
        xref += b"%010d 00000 n \n" % offset

    trailer = (
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, xref_position)
    )
    return header + body + xref + trailer


class Command(BaseCommand):
    help = (
        "Reproduce el estado de la Fase 1 (MASTER §17) usando los servicios del "
        "dominio. Solo para entornos de desarrollo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Borra los datos sembrados antes de volver a crearlos. "
            "DESTRUCTIVO: elimina clubes, membresías y las seis cuentas semilla.",
        )
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="No pide confirmación al usar --reset.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Este comando siembra datos de demostración y solo puede "
                "ejecutarse con DEBUG=True."
            )

        if options["reset"]:
            self._reset(confirm=not options["noinput"])

        if Club.objects.filter(acronym__in=["KOKOA", "MECATRÓNICA"]).exists():
            self.stdout.write(
                self.style.WARNING(
                    "Los datos semilla ya existen. Usa --reset para regenerarlos."
                )
            )
            return

        with transaction.atomic():
            paos = self._seed_paos()
            students = self._seed_students()
            clubs = self._seed_clubs()
            self._seed_custom_roles(clubs)
            self._seed_memberships(students, clubs)
            self._seed_historical_memberships(students, clubs, paos)
            self._seed_documents(clubs)

        self._report()

    # -- Reset ------------------------------------------------------------

    def _reset(self, *, confirm):
        if confirm:
            self.stdout.write(
                self.style.WARNING(
                    "Se eliminarán los clubes KOKOA y MECATRÓNICA con sus "
                    "membresías, roles y documentos, las seis cuentas semilla y "
                    "los períodos 2025-II y 2026-I."
                )
            )
            answer = input("Escribe 'si' para continuar: ")
            if answer.strip().lower() not in {"si", "sí"}:
                raise CommandError("Cancelado.")

        # Imports locales: este comando vive en 'core', que por diseño no
        # conoce a las apps del dominio. Aquí se hace la excepción porque
        # limpiar exige nombrar todo lo que puede colgar de un club.
        from apps.applications.models import MembershipApplication
        from apps.dynamicforms.models import Form
        from apps.events.models import (
            Event,
            EventAttendance,
            EventRegistration,
            EventStaff,
        )
        from apps.gbp.models import GbpDocumentProcess
        from apps.notifications.models import Notification

        with transaction.atomic():
            clubs = Club.objects.filter(acronym__in=["KOKOA", "MECATRÓNICA"])
            events = Event.objects.filter(club__in=clubs)

            # El orden va de las hojas hacia la raíz, siguiendo los PROTECT.
            # Las asistencias protegen a las inscripciones, que protegen a los
            # formularios; las solicitudes también. Borrar en otro orden falla
            # con ProtectedError, que es justo lo que queremos que pase si un
            # día alguien añade una entidad nueva y olvida incluirla aquí.
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

            students = Student.objects.filter(
                enrollment__in=seed_data.SEEDED_ENROLLMENTS
            )
            Notification.objects.filter(user__in=students).delete()
            students.delete()

            PaoPeriod.objects.filter(
                pao_period__in=[p["pao_period"] for p in seed_data.PAO_PERIODS]
            ).delete()

        self.stdout.write(self.style.SUCCESS("Datos semilla eliminados."))

    # -- Sembrado ---------------------------------------------------------

    def _seed_paos(self):
        paos = {}
        for spec in seed_data.PAO_PERIODS:
            paos[spec["pao_period"]] = create_pao(
                pao_period=spec["pao_period"],
                start_date=spec["start_date"],
                end_date=spec["end_date"],
                activate=spec["activate"],
            )
        self.stdout.write(f"  Períodos académicos: {len(paos)}")
        return paos

    def _seed_students(self):
        students = {}
        for spec in seed_data.STUDENTS:
            faculty = (
                Faculty.objects.get(code=spec["faculty"])
                if spec.get("faculty")
                else None
            )
            student = Student.objects.create_user(
                enrollment=spec["enrollment"],
                email=spec["email"],
                password=spec["password"],
                first_name=spec["first_name"],
                last_name=spec["last_name"],
                birth_date=spec.get("birth_date"),
                faculty=faculty,
                career=spec.get("career", ""),
                semester=spec.get("semester"),
                description=spec.get("description", ""),
                skills=spec.get("skills", []),
                social_media=spec.get("social_media", []),
                is_gbp_admin=spec.get("is_gbp_admin", False),
                # Cuentas ya establecidas: no vuelven a pasar por la
                # verificación de correo.
                is_verified=True,
            )
            students[spec["enrollment"]] = student
        self.stdout.write(f"  Estudiantes: {len(students)}")
        return students

    def _seed_clubs(self):
        clubs = {}
        for spec in seed_data.CLUBS:
            areas = InterestArea.objects.filter(name__in=spec["interest_areas"])
            club = create_club(
                name=spec["name"],
                acronym=spec["acronym"],
                description=spec["description"],
                location=spec["location"],
                leader_enrollment=spec["leader_enrollment"],
                faculty=Faculty.objects.get(code=spec["faculty"]),
                interest_area_ids=list(areas.values_list("id", flat=True)),
            )
            # El estado no se fija: lo decide el servicio según exista o no la
            # cuenta del líder. Se comprueba que coincida con lo esperado, para
            # que un cambio futuro en esa lógica no pase inadvertido.
            if club.status != spec["expected_status"]:
                raise CommandError(
                    f"{club.acronym} quedó en '{club.status}' y se esperaba "
                    f"'{spec['expected_status']}'."
                )
            clubs[spec["acronym"]] = club
        self.stdout.write(f"  Clubes: {len(clubs)}")
        return clubs

    def _seed_custom_roles(self, clubs):
        for spec in seed_data.CUSTOM_ROLES:
            create_role(
                club_id=clubs[spec["club"]].pk,
                role_name=spec["role_name"],
                is_leadership=spec["is_leadership"],
                permissions=spec["permissions"],
            )
        self.stdout.write(f"  Roles personalizados: {len(seed_data.CUSTOM_ROLES)}")

    def _seed_memberships(self, students, clubs):
        for spec in seed_data.MEMBERSHIPS:
            club = clubs[spec["club"]]
            create_membership(
                student=students[spec["enrollment"]],
                club=club,
                role=Role.objects.get(club=club, role_name=spec["role"]),
                origin=Membership.Origin.SEED,
            )
        # La membresía directiva de Diego la creó el alta del club.
        total = Membership.objects.count()
        self.stdout.write(f"  Membresías del período vigente: {total}")

    def _seed_historical_memberships(self, students, clubs, paos):
        """
        Crea la nómina de 2025-II y la congela.

        Se congela mediante el propio comando de transición (M2) en vez de
        escribir el estado a mano: así el dato semilla es el resultado real de
        la regla, no una afirmación sobre ella.
        """
        for spec in seed_data.HISTORICAL_MEMBERSHIPS:
            club = clubs[spec["club"]]
            create_membership(
                student=students[spec["enrollment"]],
                club=club,
                role=Role.objects.get(club=club, role_name=spec["role"]),
                pao_period=paos[spec["pao"]],
                origin=Membership.Origin.SEED,
            )

        # notify=False: nadie debe recibir hoy un aviso de un período de 2025.
        frozen = freeze_expired_memberships(
            today=seed_data.FREEZE_REFERENCE_DATE, notify=False
        )
        self.stdout.write(f"  Membresías históricas congeladas: {frozen}")

    def _seed_documents(self, clubs):
        for spec in seed_data.CLUB_DOCUMENTS:
            add_club_document(
                club_id=clubs[spec["club"]].pk,
                title=spec["title"],
                file=ContentFile(
                    build_minimal_pdf(spec["title"]), name=spec["filename"]
                ),
                is_public=spec["is_public"],
            )
        self.stdout.write(f"  Documentos: {len(seed_data.CLUB_DOCUMENTS)}")

    # -- Reporte ----------------------------------------------------------

    def _report(self):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Datos semilla creados."))
        self.stdout.write("")
        self.stdout.write("Cuentas (contraseñas del prototipo, solo desarrollo):")
        for spec in seed_data.STUDENTS:
            self.stdout.write(
                f"  {spec['enrollment']:<12} {spec['password']:<15} "
                f"{spec['first_name']} {spec['last_name']}"
            )

        self.stdout.write("")
        self.stdout.write("Qué permite probar cada dato (MASTER §17.12):")
        for dato, prueba in seed_data.COVERAGE:
            self.stdout.write(f"  {dato:<42} {prueba}")
