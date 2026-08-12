"""Bases abstractas reutilizadas por los modelos del dominio."""

from django.db import models


class TimeStampedModel(models.Model):
    """
    Marcas de tiempo de creación y modificación.

    Decisión D-04: toda entidad mutable las lleva. RF-52 exige poder auditar
    cuándo ocurrió cada cambio de estado, y reconstruir eso después de los
    hechos es imposible si no se registró desde el principio.
    """

    created_at = models.DateTimeField("creado el", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("modificado el", auto_now=True)

    class Meta:
        abstract = True
