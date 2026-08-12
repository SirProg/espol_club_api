"""
Diccionario de permisos granulares por club (MASTER §3.3) y roles por defecto.

Los permisos **no** usan el sistema ``auth.Permission`` de Django: aquel es
global y estos son por club. Un mismo estudiante puede tener ``manage_events``
en un club y ningún permiso en otro.

El bloque es extensible por diseño: agregar una capacidad nueva es agregar una
clave. Una clave ausente se interpreta como ``False``, de modo que los roles ya
existentes no heredan permisos nuevos por accidente.
"""

from django.db import models


class ClubPermission(models.TextChoices):
    ACCESS_WEB_PANEL = "access_web_panel", "Acceder al panel web del club"
    MANAGE_CLUB_INFO = "manage_club_info", "Editar datos y documentos del club"
    MANAGE_MEMBERS = "manage_members", "Administrar la nómina"
    MANAGE_ROLES = "manage_roles", "Crear roles y asignar permisos"
    MANAGE_FORMS = "manage_forms", "Usar el constructor de formularios"
    MANAGE_EVENTS = "manage_events", "Crear y editar eventos, asignar Staff"
    SCAN_EVENT_QR = "scan_event_qr", "Escanear credenciales QR"
    MANAGE_DOCUMENTS = "manage_documents", "Subir y clasificar documentos"
    SUBMIT_GBP_REPORTS = "submit_gbp_reports", "Enviar trámites a GBP"


ALL_PERMISSIONS = [choice.value for choice in ClubPermission]


def permission_set(*keys):
    """Construye el diccionario de permisos con las claves indicadas en True."""
    return {key: True for key in keys}


# Los cuatro roles que nace teniendo todo club (RF-06). Se crean en el alta y no
# se pueden borrar: 'Miembro' en particular es el rol base que recibe toda
# solicitud aprobada (RF-08), así que su ausencia rompería el flujo de membresía.
DEFAULT_ROLES = [
    {
        "role_name": "Presidente/a",
        "is_leadership": True,
        "permissions": permission_set(*ALL_PERMISSIONS),
    },
    {
        "role_name": "Vicepresidente/a",
        "is_leadership": True,
        # Sin manage_roles (RN-7), sin scan_event_qr ni submit_gbp_reports.
        "permissions": permission_set(
            ClubPermission.ACCESS_WEB_PANEL,
            ClubPermission.MANAGE_CLUB_INFO,
            ClubPermission.MANAGE_MEMBERS,
            ClubPermission.MANAGE_FORMS,
            ClubPermission.MANAGE_EVENTS,
            ClubPermission.MANAGE_DOCUMENTS,
        ),
    },
    {
        "role_name": "Secretario/a",
        "is_leadership": True,
        "permissions": permission_set(
            ClubPermission.ACCESS_WEB_PANEL,
            ClubPermission.MANAGE_MEMBERS,
            ClubPermission.MANAGE_DOCUMENTS,
        ),
    },
    {
        "role_name": "Miembro",
        "is_leadership": False,
        "permissions": {},
    },
]

#: Nombre del rol que recibe toda membresía nueva por aprobación (RF-08).
BASE_ROLE_NAME = "Miembro"

#: Nombre del rol directivo que se asigna al líder designado por GBP.
PRESIDENT_ROLE_NAME = "Presidente/a"
