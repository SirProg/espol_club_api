"""
Validadores transversales del dominio.

Todos se aplican en el servidor. Las validaciones equivalentes de MASTER §12 son
de cliente y no son confiables: el frontend puede ser reemplazado por curl.
"""

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone


def validate_espol_email(value):
    """RF-01: solo se admiten correos institucionales."""
    domain = settings.ESPOL_EMAIL_DOMAIN
    if not value or not value.strip().lower().endswith(domain):
        raise ValidationError(
            "El correo debe ser institucional (%(domain)s).",
            code="non_institutional_email",
            params={"domain": domain},
        )


def validate_not_future_date(value):
    """
    La fecha no puede estar en el futuro (fecha de nacimiento, F-02).

    Se valida en Python y no como CHECK constraint porque MariaDB no admite
    funciones no deterministas como CURRENT_DATE dentro de un CHECK.
    """
    if value and value > timezone.localdate():
        raise ValidationError(
            "La fecha no puede ser futura.",
            code="future_date",
        )


def validate_pdf_file(value):
    """
    RNF-08: los documentos del club y los trámites a GBP son solo PDF.

    Se comprueban extensión **y** content-type: renombrar un .docx a .pdf no
    debe bastar para colarlo.
    """
    extension = Path(value.name).suffix.lower()
    if extension not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            "Formato no admitido (%(ext)s). Solo se aceptan archivos PDF.",
            code="invalid_extension",
            params={"ext": extension or "sin extensión"},
        )

    content_type = getattr(value.file, "content_type", None) or getattr(
        value, "content_type", None
    )
    if content_type and content_type not in settings.ALLOWED_DOCUMENT_CONTENT_TYPES:
        raise ValidationError(
            "El contenido del archivo no corresponde a un PDF.",
            code="invalid_content_type",
        )


def validate_social_media(value):
    """
    Valida el bloque ``social_media``: ``[{"network": str, "link": url}]``.

    Se valida la forma porque es un JSONField: la base acepta cualquier
    estructura, así que si no se comprueba aquí no se comprueba en ningún lado.
    """
    if value in (None, ""):
        return
    if not isinstance(value, list):
        raise ValidationError(
            "Las redes sociales deben ser una lista.", code="invalid_structure"
        )

    url_validator = URLValidator(message="El enlace no es una URL válida.")
    for entry in value:
        if not isinstance(entry, dict):
            raise ValidationError(
                "Cada red social debe ser un objeto con 'network' y 'link'.",
                code="invalid_structure",
            )
        if not entry.get("network"):
            raise ValidationError(
                "Cada red social necesita un nombre de red.", code="missing_network"
            )
        url_validator(entry.get("link", ""))


def validate_string_list(value):
    """Valida una lista de cadenas no vacías (``skills``, áreas de interés)."""
    if value in (None, ""):
        return
    if not isinstance(value, list):
        raise ValidationError("Se esperaba una lista.", code="invalid_structure")
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                "La lista solo admite textos no vacíos.", code="invalid_item"
            )
