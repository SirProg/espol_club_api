"""
Manejador global de excepciones de la API.

Existe porque los servicios del dominio ya garantizan un contrato único: **un
comando solo falla con ``DomainError``**, y cada uno lleva su ``code`` y su
``http_status``. Traducir eso a HTTP en un solo lugar evita que cada vista
repita el mismo ``try/except``, y —más importante— evita que una vista nueva se
olvide de hacerlo y devuelva un 500 donde correspondía un 409.

**Formato de error, uniforme para toda la API:**

```json
{
  "error": {
    "code": "leadership_exclusivity",
    "message": "Diego Ponce ya lidera KOKOA...",
    "field": "leader_enrollment",
    "errors": {"campo": ["detalle"]}
  }
}
```

``field`` y ``errors`` solo aparecen cuando aportan algo. Las respuestas de
éxito **no** se envuelven: son el recurso tal cual, con el envoltorio de
paginación estándar de DRF en los listados. Envolver también el éxito obligaría
a desenvolver en cada pantalla del frontend de la Fase 1, y la Etapa 12 depende
de que la convergencia toque un solo archivo.
"""

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from core.exceptions import DomainError
from core.services import translate_validation_error

logger = logging.getLogger(__name__)


def build_error(code, message, *, field=None, errors=None):
    payload = {"code": code, "message": message}
    if field:
        payload["field"] = field
    if errors:
        payload["errors"] = errors
    return {"error": payload}


def espolclub_exception_handler(exc, context):
    """Convierte cualquier excepción en la respuesta de error del contrato."""
    view = context.get("view").__class__.__name__ if context.get("view") else "?"

    # 1. Errores del dominio: ya traen código, mensaje y status pensados.
    if isinstance(exc, DomainError):
        logger.info(
            "Regla de negocio rechazó la operación en %s: [%s] %s",
            view,
            exc.code,
            exc.message,
        )
        return Response(
            build_error(
                exc.code,
                exc.message,
                field=getattr(exc, "field", None),
                errors=getattr(exc, "errors", None),
            ),
            status=exc.http_status,
        )

    # 2. Validación de Django que no pasó por un servicio (p. ej. un validador
    #    invocado directamente en un serializer).
    if isinstance(exc, DjangoValidationError):
        domain_error = translate_validation_error(exc)
        return Response(
            build_error(
                domain_error.code, domain_error.message, errors=domain_error.errors
            ),
            status=domain_error.http_status,
        )

    # 3. Un objeto que no existe es un 404, no un 500. Los servicios usan
    #    Model.objects.get() libremente y confían en esta traducción.
    if isinstance(exc, ObjectDoesNotExist) and not isinstance(exc, Http404):
        return Response(
            build_error("not_found", "El recurso solicitado no existe."),
            status=404,
        )

    # 4. Lo que DRF ya sabe manejar (autenticación, permisos, validación de
    #    serializers, 404, throttling), reempaquetado al mismo formato.
    response = drf_exception_handler(exc, context)
    if response is not None:
        return Response(
            _normalize_drf_error(exc, response),
            status=response.status_code,
            headers=_carry_headers(response),
        )

    # 5. Nada lo reconoció: es un fallo real. Se registra completo y se
    #    devuelve un mensaje que no filtra detalles internos.
    logger.exception("Error no controlado en %s", view)
    return None


def _detail_code(value, fallback):
    """
    El código específico viaja en el ``ErrorDetail``, no en la excepción.

    ``AuthenticationFailed("...", code="invalid_credentials")`` deja
    ``default_code = 'authentication_failed'`` intacto y guarda el código real
    en ``exc.detail.code``. Leer solo ``default_code`` perdería la distinción
    entre "credenciales inválidas" y cualquier otro fallo de autenticación.
    """
    return getattr(value, "code", None) or fallback


def _normalize_drf_error(exc, response):
    code = getattr(exc, "default_code", "error")
    detail = response.data

    if isinstance(detail, dict) and "detail" in detail:
        return build_error(
            _detail_code(detail["detail"], code), str(detail["detail"])
        )

    if isinstance(detail, dict):
        # Errores de validación de serializer: {campo: [mensajes]}
        first_field = next(iter(detail), None)
        first_message = detail[first_field]
        if isinstance(first_message, (list, tuple)) and first_message:
            summary = str(first_message[0])
        else:
            summary = str(first_message)
        return build_error(
            "validation_error",
            summary,
            field=first_field if first_field != "non_field_errors" else None,
            errors=detail,
        )

    if isinstance(detail, list) and detail:
        return build_error(code, str(detail[0]))

    return build_error(code, str(detail))


def _carry_headers(response):
    """Conserva cabeceras que forman parte del contrato HTTP del error."""
    headers = {}
    for name in ("WWW-Authenticate", "Retry-After"):
        if name in response.headers:
            headers[name] = response.headers[name]
    return headers


# Se importa para que quede claro que el 405/406 de DRF también pasa por aquí.
__all__ = ["espolclub_exception_handler", "build_error", "drf_exceptions"]
