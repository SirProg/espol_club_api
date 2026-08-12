"""Bases de vista compartidas por la API."""

from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView

from apps.clubs.models import Club


class ClubScopedView(APIView):
    """
    Vista cuyo alcance es un club concreto de la URL.

    Las clases de permiso llaman a ``get_club_id()`` **antes** de ejecutar el
    handler, así que la comprobación ocurre incluso si la vista nunca llega a
    cargar el club. El objeto se resuelve una sola vez por petición.
    """

    #: Nombre del parámetro de la URL que trae el identificador del club.
    club_url_kwarg = "club_id"

    def get_club_id(self):
        return self.kwargs.get(self.club_url_kwarg)

    def get_club(self):
        if not hasattr(self, "_club"):
            self._club = get_object_or_404(Club, pk=self.get_club_id())
        return self._club
