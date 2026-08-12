"""Paginación estándar de la API."""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    Paginación por número de página, con tamaño ajustable por el cliente.

    El catálogo de clubes lo consume la app móvil con listas cortas y el panel
    web con tablas largas; que el cliente pida su tamaño evita mantener dos
    endpoints. El tope existe para que nadie pida la tabla entera de una vez.
    """

    page_size_query_param = "page_size"
    max_page_size = 100
