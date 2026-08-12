"""
Carga del archivo .env **antes** de que Django elija su módulo de settings.

Sin esto, ``DJANGO_SETTINGS_MODULE`` dentro del ``.env`` no tiene ningún efecto:
``manage.py`` y ``wsgi.py`` resuelven qué settings importar en su primera línea
útil, y el ``.env`` no se lee hasta que ``base.py`` ya se está ejecutando —es
decir, cuando la decisión ya está tomada.

El fallo que evita es silencioso y grave: en producción el proyecto arrancaría
con la configuración de desarrollo (``DEBUG=True``, sin WhiteNoise, correo a
consola) y aparentaría funcionar, porque las credenciales de base de datos sí se
leen del mismo archivo.

Este módulo no importa Django a propósito: se ejecuta antes que él.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

#: Módulo de settings cuando ni el entorno ni el .env dicen otra cosa.
#: Desarrollo, para que clonar el repositorio y ejecutar el servidor local
#: funcione sin configurar nada.
DEFAULT_SETTINGS_MODULE = "config.settings.dev"


def load_environment():
    """
    Vuelca el ``.env`` en ``os.environ`` y fija el módulo de settings.

    Las variables ya presentes en el entorno **ganan** sobre el archivo: es lo
    que permite que el panel del alojamiento, un contenedor o un comando puntual
    impongan un valor sin editar el archivo.
    """
    env_path = BASE_DIR / ".env"

    if env_path.exists():
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", DEFAULT_SETTINGS_MODULE)
    return os.environ["DJANGO_SETTINGS_MODULE"]
