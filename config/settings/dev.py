"""Entorno de desarrollo local."""

from .base import *  # noqa: F403
from .base import env_list

DEBUG = True

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1") + ["testserver"]

# En desarrollo los correos (verificación de cuenta, recuperación) se imprimen
# en la consola en vez de enviarse.
MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}
