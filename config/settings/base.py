"""
Settings comunes a todos los entornos de ESPOLCLUB.

Los valores sensibles y los que cambian entre máquinas se leen del archivo .env
(ver .env.example). Nada de credenciales en este archivo.
"""

import datetime
import os
from pathlib import Path

from dotenv import load_dotenv

# config/settings/base.py -> config/settings -> config -> raíz del repo
BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    return env(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Núcleo
# ---------------------------------------------------------------------------

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# El modelo de usuario ES el estudiante: la matrícula es la clave natural del
# negocio (MASTER §7.2). Debe estar declarado antes del primer migrate.
AUTH_USER_MODEL = "accounts.Student"

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "corsheaders",
]

# Orden según el grafo de dependencias de LOGICA_NEGOCIO.md §2.3:
# accounts, academic y catalogs no dependen de nadie; el resto se apoya en ellos.
LOCAL_APPS = [
    # Sin modelos propios: aporta contratos compartidos y los comandos de
    # alcance transversal, que Django solo descubre en apps instaladas.
    "core",
    "apps.catalogs",
    "apps.academic",
    "apps.accounts",
    "apps.clubs",
    "apps.dynamicforms",
    "apps.applications",
    "apps.events",
    "apps.gbp",
    "apps.notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CorsMiddleware debe ir lo más arriba posible y siempre antes de
    # CommonMiddleware: si no, una redirección de Common puede salir sin las
    # cabeceras CORS y el navegador la bloquea sin explicar por qué.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Base de datos — MariaDB / MySQL
# ---------------------------------------------------------------------------
#
# isolation_level "read committed": la ruta caliente del sistema es el escaneo
# de QR (CU-EV9), que toma SELECT ... FOR UPDATE sobre EventRegistration. El
# REPEATABLE READ por defecto de InnoDB añade gap locks que ahí solo aportan
# contención y riesgo de deadlock.
#
# sql_mode estricto: sin él MariaDB trunca valores en silencio en vez de fallar,
# lo que convierte un error de validación en corrupción silenciosa de datos.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME", "espolclub"),
        "USER": env("DB_USER", "espolclub"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "isolation_level": "read committed",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "TEST": {
            "CHARSET": "utf8mb4",
        },
    }
}

TEST_RUNNER = "core.test_runner.EspolclubTestRunner"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Localización
# ---------------------------------------------------------------------------
#
# RNF-10: los valores viajan a la base en inglés y se presentan en español. La
# traducción vive en las etiquetas de los TextChoices, no en la base.

LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# MEDIA_ROOT se lee del entorno porque en un alojamiento compartido conviene
# dejarlo **fuera** del directorio del código: así un despliegue que reemplace
# el árbol del proyecto no se lleva por delante los PDF de los clubes ni los
# trámites enviados a GBP.
MEDIA_URL = "media/"
MEDIA_ROOT = env("DJANGO_MEDIA_ROOT") or (BASE_DIR / "media")

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}

# ---------------------------------------------------------------------------
# API — Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # Sesión solo para la API navegable en desarrollo; nunca es la vía de
        # los clientes móvil y web, que usan JWT (RNF-04).
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Cerrado por defecto: una vista nueva nace protegida y hay que abrirla a
    # propósito. Al revés, olvidar el permiso deja el recurso público.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.api.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "core.api.exception_handler.espolclub_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # El registro y el login son los puntos que un atacante prueba en masa.
        "auth_login": "10/min",
        "auth_register": "5/hour",
        "auth_password_reset": "5/hour",
    },
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    # DRF reserva ?format= para negociar el renderer, y filtra por ese valor
    # **antes** de llegar a la vista: con el valor por defecto,
    # /gbp/processes/1/export/?format=xlsx devuelve 404 porque no existe un
    # renderer 'xlsx'. El contrato de MASTER §16.6 usa ese nombre para el
    # formato de exportación, así que se desactiva la negociación por URL. La
    # cabecera Accept sigue funcionando para lo que sí la necesita.
    "URL_FORMAT_OVERRIDE": None,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "UPDATE_LAST_LOGIN": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# El frontend estático de la Fase 1 y la app React Native consumen esta API
# desde otro origen.
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500"
)
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Parámetros de negocio
# ---------------------------------------------------------------------------
#
# Van aquí y no incrustados en el código porque son política institucional
# ajustable, no constantes del dominio.

# Dominio institucional exigido en el registro (RF-01).
ESPOL_EMAIL_DOMAIN = "@espol.edu.ec"

# Ventana de validez del escaneo de QR alrededor del evento (decisión D-08).
SCAN_LEAD_MINUTES = 120
SCAN_GRACE_MINUTES = 30

# Formatos admitidos en carga y exportación (RNF-08). Sin .doc/.docx.
ALLOWED_DOCUMENT_EXTENSIONS = [".pdf"]
ALLOWED_DOCUMENT_CONTENT_TYPES = ["application/pdf"]
ALLOWED_EXPORT_FORMATS = ["xlsx", "pdf"]

# Verificación de correo (RF-01) y recuperación de contraseña (RF-03).
EMAIL_VERIFICATION_SALT = "espolclub.email-verification"
EMAIL_VERIFICATION_MAX_AGE = 60 * 60 * 48  # 48 horas
DEFAULT_FROM_EMAIL = "no-reply@espol.edu.ec"

# Base pública sobre la que se arman los enlaces enviados por correo. En
# producción debe apuntar al dominio real del frontend.
FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", "http://localhost:5500")
