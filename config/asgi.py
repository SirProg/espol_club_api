"""Punto de entrada ASGI. Mismo criterio que ``wsgi.py``."""

from config.bootstrap import load_environment

load_environment()

from django.core.asgi import get_asgi_application  # noqa: E402

application = get_asgi_application()
