"""
Entorno de producción (AlwaysData).

Todo lo que cambia entre máquinas se lee del entorno. Este módulo no contiene
ningún valor específico del alojamiento: se puede desplegar en otro proveedor
cambiando variables, sin tocar código.
"""

from pathlib import Path

from .base import *  # noqa: F403
from .base import BASE_DIR, env, env_bool, env_list

DEBUG = False

# Sin valor por defecto a propósito: un ALLOWED_HOSTS vacío hace que Django
# rechace todas las peticiones con un error explícito. Es preferible a un
# comodín heredado que acepte cualquier Host y abra la puerta a envenenamiento
# de cabecera.
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Seguridad del transporte
# ---------------------------------------------------------------------------
#
# AlwaysData termina TLS en su proxy y reenvía la petición por HTTP. Sin esta
# cabecera Django cree que la conexión es insegura y entra en un bucle de
# redirecciones con SECURE_SSL_REDIRECT.

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Activo por defecto: hay que desactivarlo a propósito, no acordarse de
# activarlo. El interruptor existe para poder ejecutar la suite completa contra
# esta configuración antes de desplegar —el cliente de tests habla HTTP y con la
# redirección activa recibe un 301 en vez de la respuesta— y para diagnosticar
# el primer arranque si el proxy del alojamiento no reenvía X-Forwarded-Proto.
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
#
# Con la configuración por defecto (CONN_MAX_AGE=0) cada petición abre y cierra
# una conexión a MySQL. En un alojamiento compartido, donde el número de
# conexiones simultáneas está limitado por cuenta, eso agota el cupo antes que
# cualquier otro recurso.

DATABASES["default"]["CONN_MAX_AGE"] = 60  # noqa: F405
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405

# ---------------------------------------------------------------------------
# API: solo JSON
# ---------------------------------------------------------------------------
#
# En desarrollo DRF añade su "API navegable", que renderiza HTML cuando el
# cliente pide text/html —es decir, cuando abres una URL en el navegador—. En
# producción se desactiva por tres motivos:
#
# 1. Es una herramienta de depuración: los clientes reales (app móvil y panel
#    web) consumen JSON y nunca la usan.
# 2. Publica la superficie completa de la API, con sus formularios, a cualquiera
#    que abra una URL.
# 3. Su plantilla depende de {% static %}, así que con el almacenamiento por
#    manifiesto un archivo ausente convierte una petición desde el navegador en
#    un error 500, mientras la misma URL con curl responde correctamente. Ese
#    desajuste entre lo que ve un navegador y lo que ve un cliente es una fuente
#    de diagnósticos equivocados.
#
# Con esto, el navegador y curl devuelven exactamente lo mismo.
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
]

# ---------------------------------------------------------------------------
# Archivos estáticos
# ---------------------------------------------------------------------------
#
# WhiteNoise los sirve desde el propio proceso WSGI. Es lo que evita depender de
# la configuración de rutas estáticas del panel: el despliegue funciona con solo
# ejecutar collectstatic.

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # No es el de WhiteNoise directamente: ver core/storage.py. El estricto
    # convierte un archivo ausente del manifiesto en un 500 de la página
    # completa, lo que puede dejar /admin/ inaccesible por un recurso menor.
    "staticfiles": {"BACKEND": "core.storage.ResilientManifestStaticFilesStorage"},
}

MIDDLEWARE = MIDDLEWARE[:1] + [  # noqa: F405
    # Justo después de SecurityMiddleware, como exige la documentación de
    # WhiteNoise: antes de que cualquier otro middleware toque la respuesta.
    "whitenoise.middleware.WhiteNoiseMiddleware",
] + MIDDLEWARE[1:]  # noqa: F405

# ---------------------------------------------------------------------------
# Correo
# ---------------------------------------------------------------------------
#
# La verificación de cuenta (RF-01) y la recuperación de contraseña (RF-03)
# dependen de que esto funcione: sin correo saliente, nadie puede activar su
# cuenta y el sistema queda inutilizable para usuarios nuevos.

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        # Sin valor por defecto: un host inventado haría que el envío falle
        # en silencio y nadie podría verificar su cuenta.
        "HOST": env("EMAIL_HOST", ""),
        "PORT": int(env("EMAIL_PORT", "587")),
        "USER": env("EMAIL_HOST_USER", ""),
        "PASSWORD": env("EMAIL_HOST_PASSWORD", ""),
        "USE_TLS": True,
    },
}

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "")

# ---------------------------------------------------------------------------
# Registro de eventos
# ---------------------------------------------------------------------------
#
# Con DEBUG=False Django no muestra las trazas, así que sin esto un error 500
# sería invisible. Los errores van a un archivo que se puede leer por SSH.

LOG_DIR = Path(env("DJANGO_LOG_DIR") or (BASE_DIR / "logs"))

# Se crea si no existe. Sin esto, un directorio ausente hace que Django **no
# arranque**: falla al configurar el handler de logging, mucho antes de servir
# nada. Y el error es de los peores de diagnosticar, porque lo que se rompe es
# justamente el mecanismo con el que se registran los errores.
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{LOG_DIR}/espolclub.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "verbose",
        },
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["file", "console"], "level": "WARNING"},
    "loggers": {
        "django.request": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        # Las reglas de negocio rechazadas se registran en INFO: sirven para
        # entender qué está intentando la gente, y no son fallos del sistema.
        "core.api.exception_handler": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },
        "core.events": {"handlers": ["file"], "level": "INFO", "propagate": False},
    },
}
