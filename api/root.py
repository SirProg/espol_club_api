"""
Índice de la API.

Existe por una razón concreta: quien abre la URL raíz de un servicio espera
encontrar algo que le diga qué es. Un ``404`` es técnicamente correcto —no hay
recurso ahí— pero se lee como "esto está roto", y eso obliga a explicar cada vez
que se comparte el enlace.

Se sirve **JSON, no HTML**. Una página de bienvenida traería plantillas y
``{% static %}``, que es justo la dependencia que hace que un archivo ausente
tumbe una URL entera. Un diccionario no puede fallar así.
"""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.reverse import reverse


class ApiRootView(APIView):
    """``GET /`` — qué es este servicio y por dónde se entra."""

    permission_classes = [AllowAny]
    pagination_class = None

    def get(self, request):
        base = request.build_absolute_uri("/")
        return Response(
            {
                "service": "ESPOLCLUB API",
                "description": (
                    "Gestión de clubes y capítulos estudiantiles de ESPOL. "
                    "Backend de la aplicación móvil y del panel administrativo."
                ),
                "status": "ok",
                "version": "v1",
                "endpoints": f"{base}api/v1/",
                "admin": f"{base}admin/",
                "authentication": "JWT (Bearer). Ver POST /api/v1/auth/login/.",
            }
        )


class ApiV1RootView(APIView):
    """
    ``GET /api/v1/`` — índice de recursos.

    Agrupado por audiencia y no por app de Django: quien consume la API piensa
    en "lo que hace un estudiante" y "lo que hace la directiva", no en cómo está
    partido el backend por dentro.
    """

    permission_classes = [AllowAny]
    pagination_class = None

    def get(self, request):
        def url(name):
            return reverse(name, request=request)

        return Response(
            {
                "version": "v1",
                "public": {
                    "catalogs": url("api:v1:catalogs:list"),
                },
                "auth": {
                    "register": url("api:v1:auth:register"),
                    "verify": url("api:v1:auth:verify"),
                    "login": url("api:v1:auth:login"),
                    "refresh": url("api:v1:auth:refresh"),
                    "password_reset": url("api:v1:auth:password-reset"),
                    "session": url("api:v1:auth:session"),
                },
                "student": {
                    "profile": url("api:v1:students:profile"),
                    "applications": url("api:v1:students:my-applications"),
                    "credentials": url("api:v1:students:my-credentials"),
                },
                "discovery": {
                    "clubs": url("api:v1:clubs:list-create"),
                    "events": url("api:v1:events:list"),
                },
                "attendance": {
                    "scan": url("api:v1:attendance:scan"),
                },
                "notifications": url("api:v1:notifications:list"),
                "gbp": {
                    "processes": url("api:v1:gbp:inbox"),
                    "pao": url("api:v1:gbp:pao-list"),
                    "history": url("api:v1:gbp:history"),
                },
                "note": (
                    "Los recursos anidados en un club "
                    "(/clubs/{id}/members|forms|applications|events|processes/) "
                    "no se listan aquí porque dependen del club. "
                    "Ver DESPLIEGUE.md §10."
                ),
            }
        )
