"""
El esquema de los formularios dinámicos y la validación de sus respuestas.

Aquí vive **CU-FO6**, el servicio más reutilizado del sistema: lo consumen tanto
la postulación a un club (Etapa 6) como la inscripción a un evento (Etapa 7). Se
implementa una sola vez y en un solo lugar porque es la única barrera entre las
respuestas y la base: el formulario lo diseña el líder, pero quien envía las
respuestas es un cliente no confiable que puede mandar cualquier cosa.

Dos funciones y una asimetría deliberada entre ellas:

* ``validate_schema`` corre cuando el **líder** construye el formulario. Sus
  errores son de configuración.
* ``validate_responses`` corre cuando un **estudiante** lo llena. Sus errores se
  atribuyen al campo concreto, porque la app tiene que pintarlos junto a la
  pregunta que falló.
"""

import datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import models


class FieldType(models.TextChoices):
    TEXT = "text", "Texto corto"
    TEXTAREA = "textarea", "Texto largo"
    NUMBER = "number", "Número"
    DATE = "date", "Fecha"
    SELECT = "select", "Lista desplegable"
    RADIO = "radio", "Opción única"
    CHECKBOX = "checkbox", "Opción múltiple"


#: Tipos que exigen un catálogo de opciones (MASTER §7.2: mínimo 2).
CHOICE_TYPES = {FieldType.SELECT, FieldType.RADIO, FieldType.CHECKBOX}

#: El único que admite varias respuestas a la vez.
MULTI_VALUE_TYPES = {FieldType.CHECKBOX}

MIN_OPTIONS = 2

#: Claves admitidas dentro de ``validation``. Se restringen para que una regla
#: mal escrita en el constructor no se acepte en silencio y luego no se aplique.
SUPPORTED_RULES = {"max_length", "min_length", "min_value", "max_value"}


def validate_schema(fields):
    """
    Valida y normaliza el esquema completo de un formulario.

    Devuelve la lista de campos ordenada por ``order``, con las claves
    normalizadas. Lanza ``ValidationError`` con el detalle por campo.
    """
    if not isinstance(fields, list) or not fields:
        raise ValidationError(
            {"fields": "El formulario debe tener al menos un campo."},
            code="empty_schema",
        )

    normalized = []
    seen_ids = set()
    errors = {}

    for index, raw in enumerate(fields):
        label = f"fields[{index}]"
        if not isinstance(raw, dict):
            errors[label] = "Cada campo debe ser un objeto."
            continue

        try:
            field = _normalize_field(raw, index)
        except ValidationError as exc:
            errors[label] = exc.messages[0]
            continue

        if field["field_id"] in seen_ids:
            errors[label] = (
                f"El identificador '{field['field_id']}' está repetido. Las "
                "respuestas se guardan contra él, así que debe ser único."
            )
            continue

        seen_ids.add(field["field_id"])
        normalized.append(field)

    if errors:
        raise ValidationError(errors, code="invalid_schema")

    normalized.sort(key=lambda field: field["order"])
    return normalized


def _normalize_field(raw, index):
    field_id = str(raw.get("field_id") or "").strip()
    if not field_id:
        raise ValidationError("Cada campo necesita un 'field_id'.")

    label = str(raw.get("label") or "").strip()
    if not label:
        raise ValidationError(f"El campo '{field_id}' necesita una etiqueta.")

    field_type = str(raw.get("type") or "").strip()
    if field_type not in FieldType.values:
        raise ValidationError(
            f"Tipo de campo no admitido: '{field_type}'. "
            f"Admitidos: {', '.join(FieldType.values)}."
        )

    options = raw.get("options") or []
    if not isinstance(options, list):
        raise ValidationError(f"Las opciones de '{field_id}' deben ser una lista.")
    options = [str(option).strip() for option in options if str(option).strip()]

    if field_type in CHOICE_TYPES:
        if len(options) < MIN_OPTIONS:
            raise ValidationError(
                f"El campo '{field_id}' es de tipo '{field_type}' y necesita al "
                f"menos {MIN_OPTIONS} opciones."
            )
        if len(set(options)) != len(options):
            raise ValidationError(f"El campo '{field_id}' tiene opciones repetidas.")
    elif options:
        # Un campo de texto con opciones sugiere que el constructor cambió de
        # tipo y dejó basura: se rechaza en vez de ignorarlo.
        raise ValidationError(
            f"El campo '{field_id}' es de tipo '{field_type}' y no admite opciones."
        )

    validation = raw.get("validation") or {}
    if not isinstance(validation, dict):
        raise ValidationError(f"La validación de '{field_id}' debe ser un objeto.")
    unknown_rules = set(validation) - SUPPORTED_RULES
    if unknown_rules:
        raise ValidationError(
            f"Reglas de validación desconocidas en '{field_id}': "
            f"{', '.join(sorted(unknown_rules))}."
        )

    return {
        "field_id": field_id,
        "label": label,
        "type": field_type,
        "required": bool(raw.get("required", False)),
        "order": int(raw.get("order", index)),
        "options": options,
        "validation": validation,
    }


def validate_responses(schema, responses):
    """
    CU-FO6 — valida respuestas contra el esquema y las normaliza.

    Acepta las dos formas en que puede llegar el payload —el diccionario natural
    ``{field_id: answer}`` y la lista ``[{field_id, answer}]`` que es como se
    almacena— y siempre devuelve la lista, que es el formato canónico de MASTER.

    Las respuestas a campos que **no existen** en el esquema se descartan en
    silencio: no son un ataque, son un formulario que cambió de versión mientras
    alguien lo tenía abierto.
    """
    submitted = _as_answer_map(responses)
    schema_by_id = {field["field_id"]: field for field in schema}

    normalized = []
    errors = {}

    for field_id, field in schema_by_id.items():
        raw_answer = submitted.get(field_id)

        if _is_blank(raw_answer):
            if field["required"]:
                errors[field_id] = f"'{field['label']}' es obligatorio."
            else:
                normalized.append({"field_id": field_id, "answer": None})
            continue

        try:
            answer = _coerce_answer(field, raw_answer)
        except ValidationError as exc:
            errors[field_id] = exc.messages[0]
            continue

        normalized.append({"field_id": field_id, "answer": answer})

    if errors:
        raise ValidationError(errors, code="invalid_responses")

    # Se devuelve en el orden del esquema, no en el que llegó el payload.
    return normalized


def _as_answer_map(responses):
    if isinstance(responses, dict):
        return dict(responses)
    if isinstance(responses, list):
        answers = {}
        for entry in responses:
            if isinstance(entry, dict) and "field_id" in entry:
                answers[str(entry["field_id"])] = entry.get("answer")
        return answers
    raise ValidationError(
        {"responses": "Las respuestas deben ser un objeto o una lista."},
        code="invalid_responses_format",
    )


def _is_blank(value):
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, tuple)) and not value:
        return True
    return False


def _coerce_answer(field, value):
    field_type = field["type"]

    if field_type in MULTI_VALUE_TYPES:
        return _coerce_multi_choice(field, value)
    if field_type in CHOICE_TYPES:
        return _coerce_single_choice(field, value)
    if field_type == FieldType.NUMBER:
        return _coerce_number(field, value)
    if field_type == FieldType.DATE:
        return _coerce_date(field, value)
    return _coerce_text(field, value)


def _coerce_single_choice(field, value):
    answer = str(value).strip()
    if answer not in field["options"]:
        raise ValidationError(
            f"'{answer}' no es una de las opciones de '{field['label']}'."
        )
    return answer


def _coerce_multi_choice(field, value):
    values = value if isinstance(value, (list, tuple)) else [value]
    answers = [str(item).strip() for item in values]

    invalid = [item for item in answers if item not in field["options"]]
    if invalid:
        raise ValidationError(
            f"Opciones no válidas en '{field['label']}': {', '.join(invalid)}."
        )
    if len(set(answers)) != len(answers):
        raise ValidationError(f"Hay opciones repetidas en '{field['label']}'.")
    return answers


def _coerce_number(field, value):
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ValidationError(f"'{field['label']}' debe ser un número.")

    rules = field["validation"]
    if "min_value" in rules and number < Decimal(str(rules["min_value"])):
        raise ValidationError(
            f"'{field['label']}' no puede ser menor que {rules['min_value']}."
        )
    if "max_value" in rules and number > Decimal(str(rules["max_value"])):
        raise ValidationError(
            f"'{field['label']}' no puede ser mayor que {rules['max_value']}."
        )

    # Se devuelve int cuando no hay decimales para que el JSON almacenado no
    # quede con un "6.0" donde el usuario escribió "6".
    return int(number) if number == number.to_integral_value() else float(number)


def _coerce_date(field, value):
    if isinstance(value, datetime.date):
        return value.isoformat()
    try:
        return datetime.date.fromisoformat(str(value).strip()).isoformat()
    except ValueError:
        raise ValidationError(
            f"'{field['label']}' debe ser una fecha con formato AAAA-MM-DD."
        )


def _coerce_text(field, value):
    answer = str(value).strip()
    rules = field["validation"]

    max_length = rules.get("max_length")
    if max_length is not None and len(answer) > int(max_length):
        raise ValidationError(
            f"'{field['label']}' no puede superar {max_length} caracteres."
        )

    min_length = rules.get("min_length")
    if min_length is not None and len(answer) < int(min_length):
        raise ValidationError(
            f"'{field['label']}' debe tener al menos {min_length} caracteres."
        )

    return answer
