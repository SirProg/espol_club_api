#!/usr/bin/env python
"""Utilidad de línea de comandos de Django."""
import sys


def main():
    # Antes que nada: el .env decide qué settings se cargan. Si esto fuera
    # después, DJANGO_SETTINGS_MODULE dentro del .env se ignoraría y los
    # comandos correrían con la configuración de desarrollo.
    from config.bootstrap import load_environment

    load_environment()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Está instalado y disponible en el "
            "PYTHONPATH? ¿Olvidaste activar el entorno virtual?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
