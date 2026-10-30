# ESPOLCLUB — API

Backend de ESPOLCLUB: gestión de clubes y capítulos estudiantiles de la ESPOL.
Sirve una API REST con JSON al cliente web (`espol-club-web`) y a la app móvil
React Native.

Django 6.1 · Django REST Framework · SimpleJWT · MariaDB / MySQL ·
`openpyxl` y `reportlab` para exportar en Excel y PDF · WhiteNoise para los
estáticos en producción.

- **Estudiantes**: registro con correo `@espol.edu.ec`, catálogo de clubes,
  postulaciones, inscripción a eventos y credencial QR.
- **Líderes de club**: miembros, roles, formularios dinámicos, solicitudes,
  eventos, nómina y rendición de cuentas a GBP.
- **GBP**: buzón de trámites, períodos académicos (PAO) e histórico.

---

## Requisitos

| | Versión mínima | Por qué |
| :--- | :--- | :--- |
| Python | **3.12** | Lo exige Django 6.1 |
| MariaDB / MySQL | **MariaDB 10.11** o **MySQL 8.4** | Lo exige Django 6.1. MySQL 8.0 **no** sirve |

`mysqlclient` se compila al instalarlo, así que hacen falta las cabeceras de
desarrollo de MySQL/MariaDB (`libmariadb-dev` o `mysql-devel`, según la
distribución) y `pkg-config`.

## Puesta en marcha

### 1. Base de datos

```sql
CREATE DATABASE espolclub CHARACTER SET utf8mb4 COLLATE utf8mb4_uca1400_ai_ci;
CREATE USER 'espolclub'@'localhost' IDENTIFIED BY 'espolclub_dev';
GRANT ALL PRIVILEGES ON espolclub.* TO 'espolclub'@'localhost';
-- Para los tests: Django crea y borra la base test_espolclub
GRANT ALL PRIVILEGES ON test_espolclub.* TO 'espolclub'@'localhost';
```

Use una colación que ignore acentos (`_ai_`). Así el buscador de clubes encuentra
"Mecatrónica" aunque se escriba "mecatronica". En MySQL use
`utf8mb4_0900_ai_ci`.

### 2. Entorno y dependencias

Con [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

O con `pip`:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Variables de entorno

```bash
cp .env.example .env
```

Los valores de `.env.example` coinciden con la base del paso 1. Si no se define
`DJANGO_SETTINGS_MODULE`, el proyecto usa `config.settings.dev`.

### 4. Migrar, sembrar y arrancar

```bash
.venv/bin/python manage.py migrate            # también siembra facultades y áreas
.venv/bin/python manage.py seed_espol_data    # clubes y cuentas de prueba
.venv/bin/python manage.py runserver          # http://localhost:8000
```

Para comprobar que funciona, abra `GET /api/v1/catalogs/`. Es un endpoint
público y debe devolver 8 facultades y 8 áreas de interés.

En desarrollo, los correos de verificación y de recuperación de contraseña **se
imprimen en la consola** del `runserver` en lugar de enviarse.

## Comandos de gestión

| Comando | Qué hace |
| :--- | :--- |
| `seed_espol_data` | Crea 19 clubes reales de ESPOL, unas 70 cuentas, 5 PAO, eventos, solicitudes y trámites. Admite `--reset`, `--noinput` y `--seed N`. Puede usarse en producción |
| `seed_demo_data` | Conjunto reducido del documento maestro. Solo funciona con `DEBUG=True` |
| `provision_gbp_admin <código>` | Crea o promueve una cuenta de administrador GBP. Este perfil no tiene auto-registro |
| `createsuperuser` | Crea un superusuario para `/admin/`. Se inicia sesión con la matrícula, no con un nombre de usuario |

```bash
.venv/bin/python manage.py provision_gbp_admin GBP-002 \
  --email otro@espol.edu.ec --first-name Nombre --last-name Apellido \
  --password una-contrasena --staff     # --staff: también da acceso a /admin/
```

Todas las cuentas que crea `seed_espol_data` tienen la contraseña
`espolclub2026`, y sus matrículas empiezan por `202490`. El README del cliente
web contiene la tabla de cuentas de prueba por rol.

### Tareas programadas

Hay que ejecutar estos cuatro comandos con cron (o con las tareas programadas
del alojamiento). Sin ellos, las membresías no se congelan al cerrar el período
y los QR no caducan. Ejecutarlos varias veces no repite sus efectos. Los cuatro
admiten `--dry-run` y `--now <ISO-8601>`.

| Comando | Frecuencia sugerida | Qué hace |
| :--- | :--- | :--- |
| `freeze_expired_memberships` | Diaria, 03:00 | Congela las membresías cuyo PAO terminó |
| `expire_stale_memberships` | Diaria, 03:15 | Expira las membresías congeladas que nadie renovó |
| `expire_qr_tokens` | Cada hora | Caduca los QR de los eventos que ya terminaron |
| `mark_no_shows` | Cada hora | Marca como ausentes a los inscritos que no escanearon |

Ejecútelos **desde el directorio del proyecto**, para que `manage.py` encuentre
el `.env`.

## Tests

```bash
.venv/bin/python manage.py test
```

Los tests usan MariaDB/MySQL igual que la aplicación, así que el usuario de la
base necesita permisos sobre `test_espolclub` (paso 1). El runner
(`core/test_runner.py`) cambia el hasher de contraseñas por uno rápido para que
la suite no tarde de más.

## La API

La API vive en `/api/v1/`. `GET /` y `GET /api/v1/` devuelven un índice de los
recursos en JSON. En desarrollo se puede recorrer con la API navegable de DRF;
en producción solo responde JSON.

### Autenticación

```
POST /api/v1/auth/login/     {"identifier": "202311346", "password": "..."}
                             identifier acepta la matrícula o el correo
                             → {"access": "...", "refresh": "..."}
POST /api/v1/auth/refresh/   {"refresh": "..."} → {"access": "..."}
```

El resto de las peticiones lleva la cabecera `Authorization: Bearer <access>`.
El token de acceso dura **30 minutos**. El de refresco dura **7 días** y se
renueva cada vez que se usa.

**No lea el rol desde el token.** Use `GET /api/v1/auth/me/`: el servidor
calcula el rol a partir de las membresías actuales, así que una revocación de
liderazgo se ve de inmediato.

Todas las vistas exigen autenticación salvo que se abran de forma explícita. El
login, el registro y la recuperación de contraseña tienen límite de peticiones
(10 por minuto, 5 por hora y 5 por hora, respectivamente).

### Recursos

| Prefijo | Contenido |
| :--- | :--- |
| `auth/` | `register`, `verify`, `verify/resend`, `login`, `refresh`, `password-reset`, `password-reset/confirm`, `me` |
| `catalogs/` | Facultades y áreas de interés (público) |
| `students/me/` | Perfil, `applications/` (historial) y `registrations/` (credenciales QR) |
| `clubs/` | Catálogo (`?q=&faculty=&area=`) y detalle |
| `clubs/{id}/…` | `members`, `nomina`, `roles`, `documents`, `leader/assign·revoke`, `forms`, `forms/membership`, `applications`, `applications/can-apply`, `events`, `processes` |
| `forms/{id}/` | `versions`, `validate`, `activate·deactivate` |
| `applications/{id}/` | `approve·reject` |
| `events/` | Listado, detalle, `staff`, `register`, `can-register`, `registrations` |
| `attendance/scan/` | Escaneo del QR por el staff (`{"qr_token": "..."}`) |
| `roles/{id}/`, `memberships/{id}/`, `club-documents/{id}/` | Operaciones sobre un elemento suelto |
| `gbp/` | `processes` (buzón, `take·review`, `export`), `pao`, `history` |
| `notifications/` | Listado y `read` |

Los formularios de postulación e inscripción son **dinámicos**: el servidor
envía el esquema en `fields` y el cliente lo dibuja.
`POST /forms/{id}/validate/` valida las respuestas sin crear nada. Las
exportaciones de GBP usan `?format=xlsx` o `?format=pdf`.

El `qr_token` es opaco: el cliente lo envía sin modificarlo a
`/attendance/scan/`.

### Errores

Todas las respuestas de error tienen la misma forma:

```json
{ "error": { "code": "already_pending",
             "message": "Ya tienes una solicitud pendiente en este club.",
             "field": "...", "errors": { "campo": ["detalle"] } } }
```

`message` está en español y se puede mostrar al usuario sin cambios. `code` no
cambia entre versiones y es el que debe usar el cliente para decidir qué hacer.

`400` validación · `401` sin autenticar · `403` sin permiso · `404` no existe ·
`409` regla de negocio o conflicto de estado · `429` demasiadas peticiones.

## Estructura

```
config/
  bootstrap.py   lee el .env ANTES de que Django elija sus settings
  settings/      base.py · dev.py · prod.py
api/
  root.py        índices JSON de / y /api/v1/
  v1/            una carpeta por recurso: urls · views · serializers
  tests/         tests de la API
apps/            dominio: models · services · selectors · admin · tests
  accounts       Student es el modelo de usuario (la matrícula es la clave)
  academic       períodos PAO
  catalogs       facultades y áreas
  clubs          clubes, membresías, roles, liderazgo y políticas
  dynamicforms   esquema y validación de formularios
  applications   postulaciones
  events         eventos, inscripción, QR y asistencia
  gbp            trámites y exportaciones
  notifications  notificaciones y tareas programadas
core/            piezas compartidas: manejo de errores, paginación,
                 permisos, eventos de dominio y siembra de datos
```

La lógica de negocio está en `apps/*/services` (escrituras) y
`apps/*/selectors.py` (lecturas). Las vistas de `api/v1/` solo traducen HTTP a
esas llamadas.

## Producción

`config/settings/prod.py` está pensado para AlwaysData, pero todos sus valores
vienen de variables de entorno, así que sirve para cualquier alojamiento con
WSGI. Defina `DJANGO_SETTINGS_MODULE=config.settings.prod` en el `.env` y
complete el bloque *Solo producción* de `.env.example`. Además:

- `FRONTEND_BASE_URL`: el dominio del cliente web. Si falta, los enlaces de los
  correos apuntan a `localhost`.
- `CORS_ALLOWED_ORIGINS`: los orígenes del panel web y de la app.
- `DJANGO_ALLOWED_HOSTS` **no tiene valor por defecto**. Si queda vacío, Django
  rechaza todas las peticiones.

Producción obliga a usar HTTPS (redirección y HSTS) y espera que el proxy envíe
la cabecera `X-Forwarded-Proto`. Los errores se guardan en
`$DJANGO_LOG_DIR/espolclub.log`.

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

Antes de empezar a operar, cree un **PAO activo** desde `/admin/` o desde
`POST /api/v1/gbp/pao/`. Sin él, aprobar solicitudes o renovar nóminas falla.
Configure también las tareas programadas.

La guía completa, paso a paso, está en [`DESPLIEGUE.md`](./DESPLIEGUE.md)
(AlwaysData, con el web en InfinityFree), que es el despliegue actual. Como
alternativa en evaluación, con el API y el web en una sola instancia de AWS
Lightsail, ver [`DESPLIEGUE_AWS.md`](./DESPLIEGUE_AWS.md).
