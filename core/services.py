"""
Base transaccional de los comandos del dominio.

Un *comando* es una función que muta estado. Todas comparten la misma forma:
corren dentro de una transacción y traducen los errores de integridad de la base
a errores de negocio legibles.

Por qué la traducción importa: los invariantes I-08, I-09 e I-10 se defienden con
índices únicos sobre columnas generadas (MariaDB/MySQL no soportan índices
parciales). Bajo concurrencia, la validación en Python puede pasar y el índice
disparar después. Sin traducir, ese caso sale como un 500 con un mensaje de
MariaDB; traducido, sale como el mismo error de negocio que habría dado la
validación previa.
"""

import functools
import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction

from core.exceptions import BusinessRuleViolation, DomainError, DomainValidationError

#: Cómo deben llamar los servicios a ``full_clean()``.
#:
#: La unicidad se deja en manos de la base de datos a propósito. Si ``full_clean``
#: la validara, un nombre de rol duplicado saldría como ValidationError genérico
#: ("Rol con este Club y Nombre del rol ya existe"), mientras que el mismo choque
#: bajo concurrencia saldría como IntegrityError con el mensaje curado del
#: registro. Un solo camino evita que el error dependa de quién llegó primero.
CLEAN_WITHOUT_UNIQUENESS = {"validate_unique": False, "validate_constraints": False}

#: nombre del constraint en la base -> (mensaje para el usuario, código)
_constraint_messages: dict[str, tuple[str, str]] = {}

# Formatos de error que hay que reconocer:
#   MariaDB  1062: Duplicate entry 'X' for key 'uniq_single_active_pao'
#   MySQL 8  1062: Duplicate entry 'X' for key 'tabla.uniq_single_active_pao'
#   MariaDB  4025: CONSTRAINT `chk_pao_end_after_start` failed for `db`.`tabla`
#   MySQL 8  3819: Check constraint 'chk_pao_end_after_start' is violated.
_DUPLICATE_KEY = re.compile(r"for key '([^']+)'")
_CHECK_FAILED = re.compile(r"CONSTRAINT [`'\"]([^`'\"]+)[`'\"] failed")
_CHECK_VIOLATED = re.compile(r"Check constraint '([^']+)' is violated")


def register_constraint_message(constraint_name, message, code=None):
    """
    Asocia un constraint de base de datos con su mensaje de negocio.

    Cada app registra los suyos en el ``AppConfig.ready()``, junto al modelo que
    los declara, para que el mensaje viva al lado de la regla que lo produce.

    ``constraint_name`` debe ser el nombre **real** del índice o constraint en la
    base, no el que uno supondría. Para un ``UniqueConstraint`` con ``name=`` es
    ese nombre; para un campo con ``unique=True``, MariaDB nombra el índice
    según la columna (``enrollment``, no ``accounts_student_enrollment``).
    Comprobable con:

        SELECT INDEX_NAME FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=... AND NON_UNIQUE=0;
    """
    _constraint_messages[constraint_name] = (message, code or constraint_name)


def extract_constraint_name(exc):
    """
    Devuelve el nombre del constraint que disparó el error, o ``None``.

    Se extrae con precisión en vez de buscar por subcadena: nombres cortos como
    ``email`` aparecerían dentro de cualquier mensaje que mencione un correo y
    producirían traducciones equivocadas.
    """
    text = str(exc)
    for pattern in (_DUPLICATE_KEY, _CHECK_FAILED, _CHECK_VIOLATED):
        match = pattern.search(text)
        if match:
            # MySQL 8 antepone el nombre de la tabla; MariaDB no.
            return match.group(1).rsplit(".", 1)[-1]
    return None


def translate_integrity_error(exc):
    """Convierte un ``IntegrityError`` en el ``DomainError`` que le corresponde."""
    name = extract_constraint_name(exc)
    if name and name in _constraint_messages:
        message, code = _constraint_messages[name]
        return BusinessRuleViolation(message, code=code)
    return BusinessRuleViolation(
        "La operación choca con una restricción de integridad de los datos.",
        code="integrity_error",
    )


def translate_validation_error(exc):
    """
    Convierte el ``ValidationError`` de Django en ``DomainValidationError``.

    Conserva el detalle por campo y usa el primer mensaje como resumen, que es
    lo que se muestra cuando el consumidor no sabe pintar errores por campo.
    """
    if hasattr(exc, "message_dict"):
        errors = exc.message_dict
    else:
        errors = {"__all__": list(exc.messages)}

    summary = None
    for messages in errors.values():
        if messages:
            summary = messages[0]
            break

    return DomainValidationError(errors=errors, message=summary)


def command(func):
    """
    Marca una función como comando del dominio: transaccional y traducida.

    Garantiza el contrato de salida: **un comando solo falla con DomainError**.
    Los ``DomainError`` levantados adentro se dejan pasar tal cual; los errores
    de validación de Django y los de integridad de la base se traducen.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            with transaction.atomic():
                return func(*args, **kwargs)
        except DomainError:
            raise
        except DjangoValidationError as exc:
            raise translate_validation_error(exc) from exc
        except IntegrityError as exc:
            raise translate_integrity_error(exc) from exc

    wrapper.is_command = True
    return wrapper
