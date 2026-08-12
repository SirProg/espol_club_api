"""Rutas raíz del proyecto ESPOLCLUB."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from api.root import ApiRootView

urlpatterns = [
    # Índice del servicio: sin él, la raíz devuelve un 404 que se lee
    # como "esto está caído" aunque la API funcione.
    path("", ApiRootView.as_view(), name="api-root"),
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]

if settings.DEBUG:
    # En desarrollo Django sirve los PDF de los clubes; en producción lo hace el
    # servidor web y esta rama no se activa.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
