"""
Punto de entrada WSGI.

AlwaysData apunta su sitio a este archivo y espera encontrar el callable
``application``. El módulo de settings se toma de la variable de entorno
DJANGO_SETTINGS_MODULE, que se define en el panel del sitio; el valor por
defecto es el de desarrollo para que ejecutar el servidor local siga siendo
posible sin configurar nada.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

application = get_wsgi_application()
