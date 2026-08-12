# Despliegue de la API ESPOLCLUB en AlwaysData

Guía completa para publicar el backend Django y su base de datos.

---

## 0. Antes de empezar: dos requisitos que pueden bloquearte

Compruébalos **primero**. Si alguno no se cumple, el resto de la guía no sirve.

### 0.1 Versión del motor de base de datos

Django 6.1 exige **MySQL ≥ 8.4** o **MariaDB ≥ 10.11**. Está verificado en el
código del propio Django (`django/db/backends/mysql/features.py`):

```python
def minimum_database_version(self):
    if self.connection.mysql_is_mariadb:
        return (10, 11)
    else:
        return (8, 4)
```

AlwaysData ofrece ambos motores, pero **la versión de MySQL suele ser 8.0**, que
no alcanza. Al crear la base, en *Bases de datos → MySQL*, revisa la versión
disponible:

- Si es **MySQL 8.4 o superior** → sirve.
- Si es **MySQL 8.0** → usa **MariaDB** (AlwaysData la ofrece en versiones
  recientes) o el `migrate` fallará de entrada con un error de versión mínima.

El proyecto funciona igual con cualquiera de los dos: usa el mismo backend de
Django y el mismo driver. Lo desarrollamos sobre MariaDB 12.3.

> **Por qué importa tanto.** Tres invariantes del sistema —un solo período
> activo, un solo liderazgo por estudiante y una sola solicitud pendiente por
> club— se defienden con **columnas generadas `STORED` + índice único**, porque
> MySQL y MariaDB no soportan índices parciales. Si el motor no las soporta, esas
> reglas dejan de estar protegidas por la base de datos.

### 0.2 Versión de Python

Django 6.1 requiere **Python ≥ 3.12**. En AlwaysData se elige en la
configuración del sitio. Si la versión más alta disponible en tu cuenta fuera
3.11, habría que bajar Django a la serie 5.2 LTS, lo que implica revisar
`GeneratedField` (disponible desde Django 5.0, así que seguiría funcionando).

---

## 1. Crear la base de datos

En el panel: **Bases de datos → MySQL → Añadir una base de datos**.

| Campo | Valor |
| :--- | :--- |
| Nombre | `api` — AlwaysData le antepone la cuenta y queda `espol-club_api` |
| Usuario | crea uno dedicado, no uses el administrador de la cuenta |
| Codificación | **`utf8mb4`** |
| Colación | `utf8mb4_uca1400_ai_ci` (MariaDB) o `utf8mb4_0900_ai_ci` (MySQL) |

La colación debe ser *accent-insensitive* (`_ai_`) a propósito: el catálogo de
clubes se busca por nombre (RF-46) y "Mecatrónica" tiene que encontrarse
escribiendo "mecatronica".

Anota **host, nombre, usuario y contraseña**: van al archivo `.env` del paso 4.

---

## 2. Subir el código

### Opción A — Git (recomendada)

Por SSH, en tu cuenta de AlwaysData:

```bash
ssh espol-club@ssh-espol-club.alwaysdata.net
cd ~/www
git clone https://github.com/SirProg/espol_club_api.git
cd espol_club_api
```

Actualizar después es `git pull` más los pasos 5 y 6.

### Opción B — SFTP

Sube el proyecto a `~/www/espol_club_api/`. **No subas** `.venv/`, `staticfiles/`,
`media/`, `logs/`, `__pycache__/` ni `.env` — el `.gitignore` ya los excluye.

### Antes de seguir: el sitio estático por defecto

AlwaysData crea una cuenta con un sitio que sirve `~/www/` como archivos
estáticos —de ahí el `index.html` que encuentras ahí—. Si sigue activo, **todo
lo que pongas bajo `~/www/` queda accesible desde el navegador**, incluido el
`.env` que vas a crear en el paso 4, con la contraseña de la base de datos, la
del correo y la `SECRET_KEY`.

Compruébalo en cuanto tengas el `.env`:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://espol-club.alwaysdata.net/espol_club_api/.env
```

`404` o `403` está bien. Si responde **`200`**, borra o reconfigura ese sitio en
*Web → Sitios* y **cambia las tres contraseñas**: hay que darlas por
comprometidas.

---

## 3. Entorno virtual y dependencias

```bash
cd ~/www/espol_club_api
python3.12 -m venv ~/venv-espolclub
~/venv-espolclub/bin/pip install --upgrade pip
~/venv-espolclub/bin/pip install -r requirements.txt
```

El entorno virtual va **fuera** del directorio del proyecto a propósito: así un
`git pull` o una resubida por SFTP no lo tocan.

> Si `mysqlclient` falla al compilar, es que faltan las cabeceras de desarrollo
> de MySQL. En AlwaysData suelen estar; si no, instala `mysqlclient` desde una
> rueda precompilada o usa `pymysql` como alternativa.

---

## 4. Variables de entorno

Crea `~/www/espol_club_api/.env` (no se versiona) con:

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=<pega aquí la clave generada abajo>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=espol-club.alwaysdata.net
DJANGO_CSRF_TRUSTED_ORIGINS=https://espol-club.alwaysdata.net

DB_NAME=espol-club_api
DB_USER=espol-club
DB_PASSWORD=<la contraseña del paso 1>
DB_HOST=mysql-espol-club.alwaysdata.net
DB_PORT=3306

# Fuera del árbol del proyecto: un despliegue no debe borrar los PDF subidos.
DJANGO_MEDIA_ROOT=/home/espol-club/media
DJANGO_LOG_DIR=/home/espol-club/logs

# Correo: sin esto nadie puede verificar su cuenta (RF-01) ni recuperar
# su contraseña (RF-03), y el sistema queda inutilizable para usuarios nuevos.
EMAIL_HOST=smtp-espol-club.alwaysdata.net
EMAIL_PORT=587
EMAIL_HOST_USER=no-reply@espol-club.alwaysdata.net
EMAIL_HOST_PASSWORD=<contraseña del buzón>
DEFAULT_FROM_EMAIL=no-reply@espol-club.alwaysdata.net

# Orígenes del frontend que consumirá la API (la app React Native en desarrollo
# con Expo, y el dominio del panel web cuando exista).
CORS_ALLOWED_ORIGINS=http://localhost:8081,http://localhost:19006
```

Genera la clave secreta con:

```bash
~/venv-espolclub/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Crea el directorio de subidas (el de logs se crea solo al arrancar):

```bash
mkdir -p /home/espol-club/media
```

---

## 5. Migraciones y datos iniciales

```bash
cd ~/www/espol_club_api

# No hace falta exportar nada: manage.py lee el .env antes de arrancar Django,
# y de ahí toma también DJANGO_SETTINGS_MODULE.
~/venv-espolclub/bin/python manage.py migrate
~/venv-espolclub/bin/python manage.py collectstatic --noinput
```

`migrate` crea las tablas **y siembra los catálogos** (7 facultades y 8 áreas de
interés) mediante una migración de datos idempotente.

### Cuenta de administración

```bash
# Superusuario para /admin/ (el login es por matrícula, no por username)
~/venv-espolclub/bin/python manage.py createsuperuser

# Administrador GBP (no hay auto-registro para este perfil: PPD-02)
~/venv-espolclub/bin/python manage.py provision_gbp_admin GBP-001 \
    --email=arivas@espol.edu.ec --first-name=Ana --last-name=Rivas --staff
```

### Primer período académico

Casi todo el sistema depende de que exista un PAO activo: sin él, aprobar
solicitudes o renovar nóminas falla con un error de configuración explícito.
Créalo desde `/admin/` o por la API una vez desplegada.

> **No ejecutes `seed_demo_data` en producción.** Está bloqueado por diseño
> (exige `DEBUG=True`), pero conviene saberlo: crea seis cuentas con contraseñas
> conocidas.

---

## 6. Configurar el sitio web

En el panel: **Web → Sitios → Añadir un sitio**.

| Campo | Valor |
| :--- | :--- |
| Tipo | **Python WSGI** |
| Ruta de la aplicación | `/home/espol-club/www/espol_club_api/config/wsgi.py` |
| Working directory | `/home/espol-club/www/espol_club_api` |
| Python | **3.12** o superior |
| Virtualenv | `/home/espol-club/venv-espolclub` |
| Dirección | `espol-club.alwaysdata.net` (o tu dominio) |

En **Variables de entorno** del sitio, añade como mínimo:

```
DJANGO_SETTINGS_MODULE = config.settings.prod
```

El resto las lee del `.env`, pero si prefieres definirlas todas en el panel
también funciona: `.env` no pisa lo que ya está en el entorno.

Activa **HTTPS** (Let's Encrypt) desde la configuración del sitio. Es
imprescindible: los settings de producción fuerzan la redirección a HTTPS y
activan HSTS.

---

## 7. Comprobar que funciona

```bash
# 1. Configuración de seguridad: debe salir sin avisos.
~/venv-espolclub/bin/python manage.py check --deploy

# 2. La API responde.
curl -s https://espol-club.alwaysdata.net/api/v1/catalogs/ | head -c 300

# 3. El admin carga con sus estilos (verifica que collectstatic funcionó).
#    Abre https://espol-club.alwaysdata.net/admin/ en el navegador.
```

`/api/v1/catalogs/` es el endpoint ideal para la primera prueba: es público
—el formulario de registro lo necesita antes de que exista ninguna cuenta— y
devuelve las 7 facultades y 8 áreas si la base está bien migrada.

Si algo falla, el registro de errores está en `/home/espol-club/logs/espolclub.log`.

---

## 8. Tareas programadas

Cuatro procesos mantienen el estado del sistema al día. Sin ellos, las
membresías no se congelan al cerrar el período y los códigos QR no caducan.

En el panel: **Avanzado → Tareas programadas**. Para cada una, el comando es:

```
/home/espol-club/venv-espolclub/bin/python /home/espol-club/www/espol_club_api/manage.py <comando>
```

| Comando | Frecuencia | Qué hace |
| :--- | :--- | :--- |
| `freeze_expired_memberships` | Diaria (03:00) | Congela las membresías cuyo PAO venció (RF-20) |
| `expire_stale_memberships` | Diaria (03:15) | Expira las congeladas que nadie renovó (RF-19) |
| `expire_qr_tokens` | Cada hora | Caduca los QR de eventos terminados (RF-37) |
| `mark_no_shows` | Cada hora | Marca como ausentes a los inscritos sin escanear |

Los cuatro son **idempotentes**: ejecutarlos dos veces no duplica efectos ni
notificaciones. Todos aceptan `--dry-run` para ver qué tocarían sin cambiar
nada — útil para comprobarlos la primera vez:

```bash
~/venv-espolclub/bin/python manage.py freeze_expired_memberships --dry-run
```

Las tareas no necesitan variables de entorno adicionales: `manage.py` lee el
`.env` del proyecto por sí mismo. Lo único imprescindible es que el comando se
ejecute **desde el directorio del proyecto**, para que encuentre ese archivo:

```
cd /home/espol-club/www/espol_club_api && /home/espol-club/venv-espolclub/bin/python manage.py freeze_expired_memberships
```

---

## 9. Actualizar el despliegue

```bash
cd ~/www/espol_club_api
git pull
~/venv-espolclub/bin/pip install -r requirements.txt
~/venv-espolclub/bin/python manage.py migrate
~/venv-espolclub/bin/python manage.py collectstatic --noinput
```

Después, **reinicia el sitio** desde el panel (o toca `config/wsgi.py`) para que
el proceso recargue el código.

---

## 10. Para la app React Native

Cuando construyas el cliente, esto es lo que necesitas saber de la API.

**Base:** `https://espol-club.alwaysdata.net/api/v1/`

### Autenticación

```
POST /auth/login/     {"identifier": "202311346", "password": "..."}
                      identifier acepta matrícula O correo institucional
                      → {"access": "...", "refresh": "..."}

POST /auth/refresh/   {"refresh": "..."} → {"access": "..."}
```

Todas las demás peticiones llevan `Authorization: Bearer <access>`.

- El *access token* dura **30 minutos**; el *refresh*, **7 días** y rota en cada
  uso. Guarda el refresh en almacenamiento seguro (`expo-secure-store`), no en
  `AsyncStorage`.
- **No leas el rol del token.** Pide `GET /auth/me/`: el servidor lo deriva del
  estado actual de las membresías, así que refleja de inmediato una revocación
  de liderazgo que un token emitido antes seguiría afirmando.

### Formato de error, uniforme en toda la API

```json
{ "error": { "code": "already_pending",
             "message": "Ya tienes una solicitud pendiente en este club.",
             "field": "...", "errors": {"campo": ["detalle"]} } }
```

`message` está en español y **es mostrable tal cual**: los mensajes de bloqueo
son los canónicos del documento maestro. `code` es estable y sirve para decidir
qué hace la app; `field` y `errors` solo aparecen cuando aportan algo.

Códigos de estado: `400` validación · `401` sin autenticar o credenciales
inválidas · `403` sin permiso · `404` no existe · `409` regla de negocio o
conflicto de estado · `429` demasiadas peticiones.

### Endpoints por pantalla

| Pantalla | Endpoint |
| :--- | :--- |
| Catálogo de clubes | `GET /clubs/?q=&faculty=&area=` |
| Detalle de club | `GET /clubs/{id}/` — devuelve nómina solo si eres miembro |
| Postular | `GET /clubs/{id}/applications/can-apply/` → `POST /clubs/{id}/applications/` |
| Formulario de postulación | `GET /clubs/{id}/forms/membership/` |
| Eventos | `GET /events/` · `GET /events/{id}/` |
| Inscribirse | `POST /events/{id}/register/` → devuelve el `qr_token` |
| Credenciales | `GET /students/me/registrations/` |
| Escanear (staff) | `POST /attendance/scan/` con `{"qr_token": "..."}` |
| Perfil | `GET/PATCH /students/me/` |
| Historial | `GET /students/me/applications/` |
| Notificaciones | `GET /notifications/` · `POST /notifications/read/` |

Los formularios de postulación e inscripción son **dinámicos**: el esquema llega
en `fields` y la app lo renderiza. Antes de enviar, puedes validar contra el
servidor con `POST /forms/{id}/validate/` y pintar los errores por campo sin
crear nada.

### Detalle importante para el escáner

El `qr_token` es opaco: no lo interpretes ni intentes extraer de él el evento o
el estudiante. Envíalo tal cual a `/attendance/scan/`. El servidor responde con
el nombre de quien asistió, o con un `code` que distingue los casos:
`qr_already_used`, `unknown_qr_token`, `not_event_staff`, `outside_scan_window`.

---

## Resumen de la comprobación final

- [ ] Motor de base de datos ≥ MySQL 8.4 / MariaDB 10.11
- [ ] Python ≥ 3.12 en el sitio
- [ ] `migrate` sin errores y catálogos sembrados
- [ ] `check --deploy` sin avisos
- [ ] `collectstatic` ejecutado y `/admin/` con estilos
- [ ] HTTPS activo (los settings lo exigen)
- [ ] `/api/v1/catalogs/` responde con 7 facultades y 8 áreas
- [ ] Un PAO creado y activo
- [ ] Administrador GBP provisionado
- [ ] Las cuatro tareas programadas configuradas
- [ ] Correo saliente probado (registra una cuenta y comprueba que llega)
