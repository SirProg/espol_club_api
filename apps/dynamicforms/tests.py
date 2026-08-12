"""
Tests de formularios dinámicos.

El grueso está en CU-FO6: es la única barrera entre las respuestas de un cliente
no confiable y la base, y la consumen dos flujos distintos (postulación e
inscripción a evento). Un fallo aquí se propaga a los dos.
"""

import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.academic.services import create_pao
from apps.accounts.models import Student
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs.services.clubs import create_club
from apps.clubs.services.leadership import revoke_leader
from apps.dynamicforms import responses as response_registry
from apps.dynamicforms import selectors
from apps.dynamicforms.models import Form
from apps.dynamicforms.schema import validate_responses, validate_schema
from apps.dynamicforms.services import (
    create_form,
    create_new_version,
    delete_form,
    update_form,
    validate_submission,
)
from core.exceptions import BusinessRuleViolation, StateTransitionError

# Esquema equivalente al formulario 301 de MASTER §17.6.
KOKOA_SCHEMA = [
    {
        "field_id": "q1",
        "label": "¿Por qué quieres unirte?",
        "type": "textarea",
        "required": True,
        "order": 1,
        "validation": {"max_length": 500},
    },
    {
        "field_id": "q2",
        "label": "Nivel de experiencia",
        "type": "select",
        "required": True,
        "order": 2,
        "options": ["Principiante", "Intermedio", "Avanzado"],
    },
]


class SchemaValidationTests(TestCase):
    """Validación del esquema: los errores son del líder que lo construye."""

    def test_normaliza_y_ordena_los_campos(self):
        schema = validate_schema(
            [
                {"field_id": "b", "label": "Segundo", "type": "text", "order": 2},
                {"field_id": "a", "label": "Primero", "type": "text", "order": 1},
            ]
        )
        self.assertEqual([field["field_id"] for field in schema], ["a", "b"])
        self.assertFalse(schema[0]["required"])
        self.assertEqual(schema[0]["options"], [])

    def test_exige_al_menos_un_campo(self):
        with self.assertRaises(ValidationError):
            validate_schema([])

    def test_rechaza_field_id_repetido(self):
        """Las respuestas se guardan contra el field_id: repetirlo las pierde."""
        with self.assertRaises(ValidationError) as ctx:
            validate_schema(
                [
                    {"field_id": "q1", "label": "Uno", "type": "text"},
                    {"field_id": "q1", "label": "Otro", "type": "text"},
                ]
            )
        self.assertIn("repetido", str(ctx.exception))

    def test_select_exige_al_menos_dos_opciones(self):
        with self.assertRaises(ValidationError):
            validate_schema(
                [
                    {
                        "field_id": "q",
                        "label": "Nivel",
                        "type": "select",
                        "options": ["Única"],
                    }
                ]
            )

    def test_un_campo_de_texto_no_admite_opciones(self):
        """
        Sugiere que el constructor cambió de tipo y dejó basura.

        Ignorarlo en silencio dejaría un esquema con datos que nadie usa y que
        el siguiente lector interpretaría mal.
        """
        with self.assertRaises(ValidationError):
            validate_schema(
                [
                    {
                        "field_id": "q",
                        "label": "Nombre",
                        "type": "text",
                        "options": ["A", "B"],
                    }
                ]
            )

    def test_rechaza_tipo_desconocido(self):
        with self.assertRaises(ValidationError):
            validate_schema([{"field_id": "q", "label": "X", "type": "firma"}])

    def test_rechaza_reglas_de_validacion_desconocidas(self):
        with self.assertRaises(ValidationError):
            validate_schema(
                [
                    {
                        "field_id": "q",
                        "label": "X",
                        "type": "text",
                        "validation": {"debe_rimar": True},
                    }
                ]
            )


class ResponseValidationTests(TestCase):
    """CU-FO6 — los errores aquí se atribuyen al campo que falló."""

    def setUp(self):
        self.schema = validate_schema(KOKOA_SCHEMA)

    def test_acepta_el_diccionario_y_la_lista(self):
        """
        El cliente envía el diccionario natural; la base guarda la lista.

        Aceptar solo una de las dos formas obligaría a cada llamador a
        convertir, y alguno lo haría mal.
        """
        como_dict = validate_responses(
            self.schema, {"q1": "Me interesa el software libre.", "q2": "Intermedio"}
        )
        como_lista = validate_responses(
            self.schema,
            [
                {"field_id": "q1", "answer": "Me interesa el software libre."},
                {"field_id": "q2", "answer": "Intermedio"},
            ],
        )
        self.assertEqual(como_dict, como_lista)
        self.assertEqual(como_dict[0]["field_id"], "q1")

    def test_exige_los_campos_obligatorios(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_responses(self.schema, {"q2": "Intermedio"})
        self.assertIn("q1", ctx.exception.message_dict)

    def test_una_cadena_de_espacios_no_cuenta_como_respuesta(self):
        with self.assertRaises(ValidationError):
            validate_responses(self.schema, {"q1": "   ", "q2": "Intermedio"})

    def test_rechaza_una_opcion_fuera_del_catalogo(self):
        """El cliente puede enviar cualquier cosa: la lista no es una sugerencia."""
        with self.assertRaises(ValidationError) as ctx:
            validate_responses(self.schema, {"q1": "Texto", "q2": "Experto"})
        self.assertIn("q2", ctx.exception.message_dict)

    def test_aplica_max_length(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_responses(self.schema, {"q1": "x" * 501, "q2": "Intermedio"})
        self.assertIn("q1", ctx.exception.message_dict)

    def test_descarta_respuestas_a_campos_inexistentes(self):
        """
        No es un ataque: es un formulario que cambió mientras estaba abierto.

        Guardarlas dejaría datos que ningún esquema sabe interpretar.
        """
        normalized = validate_responses(
            self.schema,
            {"q1": "Texto", "q2": "Intermedio", "campo_fantasma": "algo"},
        )
        self.assertEqual([entry["field_id"] for entry in normalized], ["q1", "q2"])

    def test_los_campos_opcionales_vacios_quedan_en_none(self):
        schema = validate_schema(
            [{"field_id": "extra", "label": "Comentario", "type": "text"}]
        )
        self.assertEqual(
            validate_responses(schema, {}), [{"field_id": "extra", "answer": None}]
        )


class ResponseCoercionTests(TestCase):
    def test_numero_entero_no_se_guarda_como_decimal(self):
        schema = validate_schema(
            [{"field_id": "n", "label": "Semestre", "type": "number"}]
        )
        self.assertEqual(validate_responses(schema, {"n": "6"})[0]["answer"], 6)

    def test_numero_respeta_los_limites(self):
        schema = validate_schema(
            [
                {
                    "field_id": "n",
                    "label": "Semestre",
                    "type": "number",
                    "validation": {"min_value": 1, "max_value": 10},
                }
            ]
        )
        with self.assertRaises(ValidationError):
            validate_responses(schema, {"n": 11})

    def test_numero_no_numerico_es_rechazado(self):
        schema = validate_schema([{"field_id": "n", "label": "N", "type": "number"}])
        with self.assertRaises(ValidationError):
            validate_responses(schema, {"n": "seis"})

    def test_fecha_se_normaliza_a_iso(self):
        schema = validate_schema([{"field_id": "d", "label": "Fecha", "type": "date"}])
        self.assertEqual(
            validate_responses(schema, {"d": datetime.date(2026, 5, 1)})[0]["answer"],
            "2026-05-01",
        )

    def test_fecha_mal_formada_es_rechazada(self):
        schema = validate_schema([{"field_id": "d", "label": "Fecha", "type": "date"}])
        with self.assertRaises(ValidationError):
            validate_responses(schema, {"d": "01/05/2026"})

    def test_checkbox_admite_varias_opciones(self):
        schema = validate_schema(
            [
                {
                    "field_id": "c",
                    "label": "Intereses",
                    "type": "checkbox",
                    "options": ["Python", "React", "SQL"],
                }
            ]
        )
        answer = validate_responses(schema, {"c": ["Python", "SQL"]})[0]["answer"]
        self.assertEqual(answer, ["Python", "SQL"])

    def test_checkbox_rechaza_opciones_repetidas(self):
        schema = validate_schema(
            [
                {
                    "field_id": "c",
                    "label": "Intereses",
                    "type": "checkbox",
                    "options": ["Python", "SQL"],
                }
            ]
        )
        with self.assertRaises(ValidationError):
            validate_responses(schema, {"c": ["Python", "Python"]})


class FormServiceTestCase(TestCase):
    def setUp(self):
        create_pao(
            pao_period="2026-I",
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 9, 15),
            activate=True,
        )
        # Se restaura el registro en vez de vaciarlo: borrarlo eliminaría
        # también los contadores reales que las apps registran al arrancar,
        # y el resto de la suite correría con RF-24 desactivado.
        self.addCleanup(
            response_registry.restore_response_counters,
            response_registry.snapshot_response_counters(),
        )

        Student.objects.create_user(
            enrollment="201899001",
            email="dponce@espol.edu.ec",
            password="clave",
            first_name="Diego",
            last_name="Ponce",
            is_verified=True,
        )
        self.club = create_club(
            name="Club de Software Libre KOKOA",
            acronym="KOKOA",
            description="Software libre.",
            location="FIEC 11D",
            leader_enrollment="201899001",
            faculty=Faculty.objects.get(code="FIEC"),
            interest_area_ids=[InterestArea.objects.get(name="Tecnología").id],
        )

    def make_form(self, **kwargs):
        return create_form(
            club_id=self.club.pk,
            form_type=kwargs.get("form_type", Form.FormType.MEMBERSHIP),
            title=kwargs.get("title", "Formulario de Inscripción - KOKOA"),
            fields=kwargs.get("fields", KOKOA_SCHEMA),
        )

    def pretend_form_has_responses(self, form):
        """Simula que otra app registró respuestas contra este formulario."""
        response_registry.register_response_counter(
            "prueba", lambda candidate: 1 if candidate.pk == form.pk else 0
        )


class FormCreationTests(FormServiceTestCase):
    def test_crea_la_primera_version(self):
        form = self.make_form()

        self.assertEqual(form.version, 1)
        self.assertTrue(form.is_active)
        self.assertIsNone(form.root_id)
        self.assertEqual(form.family_id, form.pk)

    def test_el_esquema_queda_normalizado_y_ordenado(self):
        form = self.make_form()
        self.assertEqual([field["field_id"] for field in form.fields], ["q1", "q2"])

    def test_un_esquema_invalido_no_crea_nada(self):
        with self.assertRaises(Exception):
            self.make_form(fields=[{"field_id": "q", "label": "X", "type": "firma"}])
        self.assertEqual(Form.objects.count(), 0)

    def test_solo_un_formulario_de_membresia_vigente_por_club(self):
        """
        RF-25: la postulación al club es una sola puerta.

        Con dos vigentes, quedaría ambiguo cuál debe renderizar la app.
        """
        primero = self.make_form(title="Antiguo")
        segundo = self.make_form(title="Nuevo")

        primero.refresh_from_db()
        self.assertFalse(primero.is_active)
        self.assertTrue(segundo.is_active)

    def test_un_club_sin_lider_no_puede_crear_formularios(self):
        revoke_leader(club_id=self.club.pk)
        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.make_form()
        self.assertEqual(ctx.exception.code, "club_read_only")


class FormImmutabilityTests(FormServiceTestCase):
    """RF-24 / decisión D-03 — el corazón de esta etapa."""

    def test_sin_respuestas_se_edita_en_sitio(self):
        form = self.make_form()
        actualizado = update_form(form_id=form.pk, title="Otro título")

        self.assertEqual(actualizado.pk, form.pk)
        self.assertEqual(actualizado.version, 1)
        self.assertEqual(actualizado.title, "Otro título")

    def test_con_respuestas_la_edicion_se_rechaza(self):
        form = self.make_form()
        self.pretend_form_has_responses(form)

        with self.assertRaises(StateTransitionError) as ctx:
            update_form(form_id=form.pk, title="No debería poder")

        self.assertEqual(ctx.exception.code, "form_has_responses")
        # 409: el conflicto es con el estado del recurso, no con el payload.
        self.assertEqual(ctx.exception.http_status, 409)

    def test_versionar_conserva_la_version_anterior(self):
        """
        Las respuestas ya enviadas siguen apuntando a la versión con la que se
        llenaron: el histórico se lee contra las preguntas que se vieron.
        """
        v1 = self.make_form()
        self.pretend_form_has_responses(v1)

        v2 = create_new_version(
            form_id=v1.pk,
            title="Formulario 2026",
            fields=KOKOA_SCHEMA + [
                {
                    "field_id": "q3",
                    "label": "¿Cómo nos conociste?",
                    "type": "text",
                    "order": 3,
                }
            ],
        )
        v1.refresh_from_db()

        self.assertEqual(v2.version, 2)
        self.assertEqual(v2.root_id, v1.pk)
        self.assertEqual(v2.family_id, v1.pk)
        self.assertTrue(v2.is_active)
        self.assertFalse(v1.is_active)
        # La v1 sobrevive intacta, con su esquema original.
        self.assertEqual(len(v1.fields), 2)
        self.assertEqual(len(v2.fields), 3)

    def test_la_version_se_cuenta_sobre_toda_la_familia(self):
        """Versionar dos veces desde la raíz debe dar v2 y v3, no v2 y v2."""
        v1 = self.make_form()
        v2 = create_new_version(form_id=v1.pk)
        v3 = create_new_version(form_id=v2.pk)

        self.assertEqual([v2.version, v3.version], [2, 3])
        self.assertEqual(v3.root_id, v1.pk)
        self.assertEqual(selectors.get_form_family(v3).count(), 3)

    def test_con_respuestas_tampoco_se_borra(self):
        form = self.make_form()
        self.pretend_form_has_responses(form)

        with self.assertRaises(BusinessRuleViolation) as ctx:
            delete_form(form_id=form.pk)
        self.assertEqual(ctx.exception.code, "form_has_responses")

    def test_sin_respuestas_si_se_borra(self):
        form = self.make_form()
        delete_form(form_id=form.pk)
        self.assertEqual(Form.objects.count(), 0)

    def test_la_raiz_de_una_familia_no_se_borra(self):
        v1 = self.make_form()
        create_new_version(form_id=v1.pk)

        with self.assertRaises(BusinessRuleViolation) as ctx:
            delete_form(form_id=v1.pk)
        self.assertEqual(ctx.exception.code, "form_is_version_root")


class ResponseRegistryTests(FormServiceTestCase):
    """
    El registro de contadores mantiene acíclico el grafo de dependencias.

    ``dynamicforms`` no sabe quién almacena respuestas; solo que alguien
    contesta cuando se le pregunta.
    """

    def test_un_formulario_recien_creado_no_tiene_respuestas(self):
        form = self.make_form()
        self.assertFalse(response_registry.form_has_responses(form))

    def test_sin_ningun_contador_registrado_devuelve_false(self):
        """
        Caso de las primeras etapas del proyecto: nadie sabe generar respuestas.

        Vaciar el registro aquí es seguro porque ``setUp`` lo restaura al
        terminar; hacerlo sin esa red dejaría al resto de la suite corriendo con
        RF-24 desactivado.
        """
        form = self.make_form()
        response_registry.clear_response_counters()
        self.assertFalse(response_registry.form_has_responses(form))

    def test_suma_los_contadores_registrados(self):
        form = self.make_form()
        response_registry.register_response_counter("postulaciones", lambda f: 2)
        response_registry.register_response_counter("inscripciones", lambda f: 3)

        desglose = response_registry.response_breakdown(form)

        # El desglose incluye además los contadores reales que las apps
        # instaladas registran al arrancar, así que se comprueba lo aportado
        # por este test en vez de exigir el diccionario exacto.
        self.assertEqual(desglose["postulaciones"], 2)
        self.assertEqual(desglose["inscripciones"], 3)
        self.assertEqual(response_registry.count_responses(form), 5)


class SubmissionTests(FormServiceTestCase):
    def test_un_formulario_inactivo_no_acepta_respuestas(self):
        form = self.make_form()
        create_new_version(form_id=form.pk)
        form.refresh_from_db()

        with self.assertRaises(BusinessRuleViolation) as ctx:
            validate_submission(form, {"q1": "Texto", "q2": "Intermedio"})
        self.assertEqual(ctx.exception.code, "form_inactive")

    def test_devuelve_las_respuestas_normalizadas(self):
        form = self.make_form()
        normalized = validate_submission(
            form, {"q1": "  Me interesa  ", "q2": "Intermedio"}
        )

        self.assertEqual(
            normalized,
            [
                {"field_id": "q1", "answer": "Me interesa"},
                {"field_id": "q2", "answer": "Intermedio"},
            ],
        )


class SelectorTests(FormServiceTestCase):
    def test_devuelve_el_formulario_de_membresia_vigente(self):
        self.make_form(title="Antiguo")
        nuevo = self.make_form(title="Nuevo")

        self.assertEqual(
            selectors.get_active_membership_form(self.club.pk).pk, nuevo.pk
        )

    def test_sin_formulario_publicado_devuelve_none(self):
        self.assertIsNone(selectors.get_active_membership_form(self.club.pk))
