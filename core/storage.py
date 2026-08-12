"""Almacenamiento de archivos estáticos para producción."""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class ResilientManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    Igual que el almacenamiento por manifiesto, pero sin tumbar la página.

    El comportamiento por defecto de Django es *estricto*: si una plantilla pide
    con ``{% static %}`` un archivo que no está en ``staticfiles.json``, lanza
    ``ValueError: Missing staticfiles manifest entry`` y la petición entera
    termina en un 500.

    Para una API es un mal negocio. El único consumidor de ``{% static %}`` en
    este proyecto es el panel de ``/admin/``, y el manifiesto solo aporta
    nombres con hash para invalidar cachés — una comodidad. Que esa comodidad
    pueda dejar el panel completo fuera de servicio, y encima con un error que
    no explica qué archivo falta hasta que se lee la traza, es desproporcionado.

    Con ``manifest_strict = False`` un archivo ausente se sirve por su nombre
    original: se pierde la invalidación de caché de ese recurso concreto y nada
    más. El fallo pasa de "el admin no abre" a "quizá un icono se cachea de
    más".
    """

    manifest_strict = False
