# Despliegue de ESPOLCLUB en AWS Lightsail

> **Alternativa en evaluación, no es el despliegue actual.** Hoy el API corre
> en AlwaysData y el web en InfinityFree: ver [`DESPLIEGUE.md`](./DESPLIEGUE.md).
> Esta guía queda como referencia por si se decide migrar. No se ha probado
> todavía en una cuenta real de AWS.

Guía para publicar el API **y** el cliente web en una sola instancia de Amazon
Lightsail, creada y configurada con el AWS CLI. Es la alternativa a
[`DESPLIEGUE.md`](./DESPLIEGUE.md) (AlwaysData + InfinityFree).

```
                    https://TU-DOMINIO
                           │
                 ┌─────────▼──────────┐   Lightsail (Ubuntu 24.04)
                 │       nginx        │
                 │  /            → web (dist/ de Vite)
                 │  /api/ /admin/ /static/ → gunicorn → Django
                 │  /media/      → PDFs subidos
                 └─────────┬──────────┘
                           │
                     MariaDB 10.11 (local)       Amazon SES (correo)
```

Web y API comparten dominio, así que **CORS deja de intervenir**: el cliente
pide `/api/v1` en su mismo origen, igual que en desarrollo.

En toda la guía, sustituye `TU-DOMINIO` (por ejemplo `espolclub.com`) y
`TU-CORREO` por los tuyos. En los archivos que se crean en el servidor puedes
hacerlo de una vez con `sudo sed -i 's/TU-DOMINIO/espolclub.com/g' <archivo>`.

---

## 0. Requisitos

| Qué | Para qué |
| :--- | :--- |
| Cuenta de AWS | Ver el aviso sobre el plan gratuito más abajo |
| **AWS CLI v2** en tu máquina | Crear la instancia, la IP, el firewall y el correo. En Arch/CachyOS: `sudo pacman -S aws-cli-v2`; en otros sistemas, el [instalador oficial](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| **Un dominio propio** | Lightsail solo da una IP. Sin dominio no hay certificado HTTPS, y los settings de producción exigen HTTPS. Sirve cualquier registrador |
| Node.js y npm | Compilar el cliente web en tu máquina |
| `ssh` y `rsync` | Entrar al servidor y subir el build del web |

> **El plan gratuito no es hosting gratuito.** Las cuentas nuevas reciben
> créditos (de $100 a $200) con un plan que dura como máximo 6 meses; al
> terminar, hay que pasar al plan de pago o se pierden los recursos. Confírmalo
> en la [FAQ del Free Tier](https://aws.amazon.com/free/free-tier-faqs/) antes
> de empezar, y crea un presupuesto con alerta (paso 1.3).

### Costo mensual aproximado

| Recurso | Costo |
| :--- | :--- |
| Instancia de 2 GB | ~$12 (consulta el precio actual en el paso 2.1) |
| IP estática | Gratis mientras esté asociada a una instancia |
| Snapshots automáticos | Cobro por GB almacenado |
| SES | Céntimos al mes con el volumen de un club |
| Dominio | ~$10–15 **al año**, según el registrador |

---

## 1. Preparar el AWS CLI

### 1.1 Un usuario con permisos acotados

No uses la cuenta raíz. En la consola de IAM, crea un usuario `espolclub-deploy`
con esta política (o usa IAM Identity Center si tu organización lo tiene):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["lightsail:*", "ses:*"], "Resource": "*" },
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateUser", "iam:PutUserPolicy", "iam:CreateAccessKey",
        "iam:GetUser", "iam:ListAccessKeys"
      ],
      "Resource": "arn:aws:iam::*:user/espolclub-ses-smtp"
    },
    { "Effect": "Allow", "Action": "budgets:*", "Resource": "*" }
  ]
}
```

El bloque de IAM solo permite crear el usuario que enviará correo (paso 6).

### 1.2 Configurar el perfil

```bash
aws configure --profile espolclub
# AWS Access Key ID:     (la del usuario espolclub-deploy)
# AWS Secret Access Key: (ídem)
# Default region name:   us-east-1
# Default output format: json

export AWS_PROFILE=espolclub
aws sts get-caller-identity          # debe mostrar el usuario espolclub-deploy
```

`us-east-1` (Virginia) tiene Lightsail y SES, y es de las regiones con menor
latencia desde Ecuador. Todos los comandos de esta guía asumen
`AWS_PROFILE=espolclub` exportado.

### 1.3 Alerta de gasto

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws budgets create-budget --account-id "$ACCOUNT_ID" \
  --budget '{"BudgetName":"espolclub","BudgetLimit":{"Amount":"20","Unit":"USD"},
             "TimeUnit":"MONTHLY","BudgetType":"COST"}' \
  --notifications-with-subscribers '[{
     "Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN",
                     "Threshold":80,"ThresholdType":"PERCENTAGE"},
     "Subscribers":[{"SubscriptionType":"EMAIL","Address":"TU-CORREO"}]}]'
```

---

## 2. Crear la instancia

### 2.1 Elegir imagen y plan

```bash
# Imagen: debe aparecer ubuntu_24_04
aws lightsail get-blueprints \
  --query "blueprints[?platform=='LINUX_UNIX' && starts_with(blueprintId,'ubuntu')].[blueprintId,name,version]" \
  --output table

# Planes con IPv4 pública (los *_ipv6_* no tienen IPv4, y GitHub, PyPI y
# muchos clientes todavía la necesitan)
aws lightsail get-bundles \
  --query "bundles[?supportedPlatforms[0]=='LINUX_UNIX' && !contains(bundleId,'ipv6')].[bundleId,price,ramSizeInGb,cpuCount,diskSizeInGb]" \
  --output table
```

Elige el plan de **2 GB de RAM**. Con 1 GB, Django, gunicorn y MariaDB juntos
funcionan, pero `pip install` y los picos de tráfico (la feria de clubes, el
escaneo de QR al empezar un evento) lo dejan sin memoria.

### 2.2 Llave SSH, instancia, IP y firewall

```bash
INSTANCE=espolclub
BUNDLE=small_3_0          # el bundleId de 2 GB que mostró el paso 2.1

# Lightsail genera la llave y devuelve la parte privada una sola vez
aws lightsail create-key-pair --key-pair-name espolclub \
  --query privateKeyBase64 --output text > ~/.ssh/espolclub-lightsail.pem
chmod 600 ~/.ssh/espolclub-lightsail.pem

aws lightsail create-instances \
  --instance-names "$INSTANCE" \
  --availability-zone us-east-1a \
  --blueprint-id ubuntu_24_04 \
  --bundle-id "$BUNDLE" \
  --key-pair-name espolclub

# Esperar a que arranque
aws lightsail get-instance-state --instance-name "$INSTANCE" --query state.name

# IP fija: sin ella, la IP cambia al reiniciar y el dominio deja de apuntar
aws lightsail allocate-static-ip --static-ip-name espolclub-ip
aws lightsail attach-static-ip --static-ip-name espolclub-ip --instance-name "$INSTANCE"
IP=$(aws lightsail get-static-ip --static-ip-name espolclub-ip \
     --query staticIp.ipAddress --output text)
echo "$IP"

# Firewall: solo SSH, HTTP y HTTPS. Reemplaza los puertos abiertos por defecto.
aws lightsail put-instance-public-ports --instance-name "$INSTANCE" --port-infos \
  fromPort=22,toPort=22,protocol=tcp \
  fromPort=80,toPort=80,protocol=tcp \
  fromPort=443,toPort=443,protocol=tcp

# Snapshot diario de la instancia completa (hora en UTC)
aws lightsail enable-add-on --resource-name "$INSTANCE" \
  --add-on-request 'addOnType=AutoSnapshot,autoSnapshotAddOnRequest={snapshotTimeOfDay=08:00}'
```

Para limitar SSH a tu IP, añade `cidrs=TU.IP.PUB.LICA/32` a la regla del
puerto 22.

### 2.3 Apuntar el dominio

En tu registrador, crea un registro **A** de `TU-DOMINIO` a la IP anterior.
Comprueba que ya resuelve antes de seguir, porque el paso 5 lo necesita:

```bash
dig +short TU-DOMINIO          # debe devolver la IP estática
```

---

## 3. Preparar el servidor

```bash
ssh -i ~/.ssh/espolclub-lightsail.pem ubuntu@"$IP"
```

Todo lo que sigue hasta el paso 7 se ejecuta **dentro del servidor**.

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install nginx mariadb-server git rsync \
  python3-venv python3-dev build-essential pkg-config libmariadb-dev \
  certbot python3-certbot-nginx

python3 --version      # 3.12: el mínimo de Django 6.1
mariadb --version      # 10.11: el mínimo de Django 6.1

# Las tareas programadas del paso 7 usan la hora del sistema. Django tiene su
# propia zona (America/Guayaquil), pero cron no la conoce.
sudo timedatectl set-timezone America/Guayaquil

# Usuario sin privilegios para la aplicación, y su árbol de directorios
sudo adduser --system --group --home /srv/espolclub espolclub
sudo -u espolclub mkdir -p /srv/espolclub/{media,logs,backups,web}
```

| Ruta | Contenido |
| :--- | :--- |
| `/srv/espolclub/api` | El repositorio del API |
| `/srv/espolclub/venv` | Entorno virtual, fuera del repositorio para que `git pull` no lo toque |
| `/srv/espolclub/web` | El `dist/` del cliente web |
| `/srv/espolclub/media` | PDFs subidos, fuera del código: un despliegue no los borra |
| `/srv/espolclub/logs` | `espolclub.log` (errores de Django) |
| `/srv/espolclub/backups` | Volcados diarios de la base |

### 3.1 Base de datos

```bash
DB_PASSWORD=$(openssl rand -base64 24)
echo "Guarda esta contraseña: $DB_PASSWORD"

sudo mariadb <<SQL
CREATE DATABASE espolclub CHARACTER SET utf8mb4 COLLATE utf8mb4_uca1400_ai_ci;
CREATE USER 'espolclub'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON espolclub.* TO 'espolclub'@'localhost';
SQL

# Credenciales para el volcado diario del paso 7. En un archivo y no en el
# comando: lo que se pasa como argumento lo ve cualquiera con `ps`.
sudo -u espolclub tee /srv/espolclub/.my.cnf > /dev/null <<EOF
[client]
user=espolclub
password=$DB_PASSWORD
EOF
sudo chmod 600 /srv/espolclub/.my.cnf
```

La colación `_ai_` no es opcional: hace que buscar "mecatronica" encuentre
"Mecatrónica". MariaDB escucha solo en `localhost` por defecto y el firewall no
abre el 3306, así que la base no queda expuesta.

### 3.2 Código y dependencias

```bash
sudo -u espolclub git clone https://github.com/SirProg/espol_club_api.git /srv/espolclub/api
sudo -u espolclub python3 -m venv /srv/espolclub/venv
sudo -u espolclub /srv/espolclub/venv/bin/pip install --upgrade pip
sudo -u espolclub /srv/espolclub/venv/bin/pip install -r /srv/espolclub/api/requirements.txt
# AlwaysData trae su propio servidor WSGI; aquí hace falta uno
sudo -u espolclub /srv/espolclub/venv/bin/pip install "gunicorn==23.0.0"
```

---

## 4. Variables de entorno

```bash
SECRET=$(/srv/espolclub/venv/bin/python -c \
  "from django.core.management.utils import get_random_secret_key as k; print(k())")

sudo -u espolclub tee /srv/espolclub/api/.env > /dev/null <<EOF
DJANGO_SETTINGS_MODULE=config.settings.prod
# Entre comillas simples: la clave puede llevar $ o #, y así el .env no los
# interpreta.
DJANGO_SECRET_KEY='$SECRET'
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=TU-DOMINIO
DJANGO_CSRF_TRUSTED_ORIGINS=https://TU-DOMINIO

DB_NAME=espolclub
DB_USER=espolclub
DB_PASSWORD=$DB_PASSWORD
DB_HOST=127.0.0.1
DB_PORT=3306

DJANGO_MEDIA_ROOT=/srv/espolclub/media
DJANGO_LOG_DIR=/srv/espolclub/logs

# Mismo origen que el web: CORS no interviene, pero se declara por si la app
# móvil o un panel en otro dominio consumen el API.
CORS_ALLOWED_ORIGINS=https://TU-DOMINIO
# Base de los enlaces de los correos de verificación y recuperación
FRONTEND_BASE_URL=https://TU-DOMINIO

# Correo: se completa en el paso 6
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=no-reply@TU-DOMINIO
EOF
sudo chmod 600 /srv/espolclub/api/.env
```

Son los mismos nombres de variable que en AlwaysData: **el código no cambia**.
`config/settings/prod.py` ya lee todo del entorno y confía en la cabecera
`X-Forwarded-Proto`, que nginx envía en el paso 5.

### 4.1 Migrar, sembrar y comprobar

```bash
cd /srv/espolclub/api
M="sudo -u espolclub /srv/espolclub/venv/bin/python manage.py"

$M migrate
$M collectstatic --noinput
$M check --deploy

$M createsuperuser                      # el login es por matrícula
$M provision_gbp_admin GBP-001 --email=CORREO@espol.edu.ec \
   --first-name=Nombre --last-name=Apellido --staff
$M seed_espol_data                      # opcional: clubes reales y cuentas de demostración
```

`seed_espol_data` crea el PAO activo. Si no lo usas, crea uno desde `/admin/`:
sin PAO activo, aprobar solicitudes o renovar nóminas falla.

---

## 5. gunicorn y nginx

### 5.1 Servicio de gunicorn

```bash
sudo tee /etc/systemd/system/espolclub.service > /dev/null <<'EOF'
[Unit]
Description=ESPOLCLUB API (gunicorn)
After=network.target mariadb.service

[Service]
User=espolclub
Group=www-data
WorkingDirectory=/srv/espolclub/api
RuntimeDirectory=espolclub
ExecStart=/srv/espolclub/venv/bin/gunicorn config.wsgi:application \
  --bind unix:/run/espolclub/gunicorn.sock \
  --workers 3 --timeout 60 \
  --access-logfile - --error-logfile -
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now espolclub
sudo systemctl status espolclub --no-pager
```

`config/wsgi.py` lee el `.env` antes de cargar Django, así que el servicio no
necesita variables propias. Tres workers caben en 2 GB; con 1 GB, usa dos.

### 5.2 Sitio de nginx

```bash
sudo tee /etc/nginx/sites-available/espolclub > /dev/null <<'EOF'
upstream espolclub_api {
    server unix:/run/espolclub/gunicorn.sock;
}

server {
    listen 80;
    server_name TU-DOMINIO;

    # Los PDF de clubes y trámites ante GBP
    client_max_body_size 20M;

    # API, admin y sus estáticos (los sirve WhiteNoise desde Django)
    location ~ ^/(api|admin|static)/ {
        proxy_pass http://espolclub_api;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        # Sin esto Django cree que la conexión es HTTP y entra en un bucle de
        # redirecciones con SECURE_SSL_REDIRECT.
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Archivos subidos. En producción Django no los sirve.
    location /media/ {
        alias /srv/espolclub/media/;
    }

    # Cliente web (SPA)
    root /srv/espolclub/web;

    # El service worker nunca se cachea: decide si el resto se actualiza.
    location = /sw.js {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
    location = /index.html {
        add_header Cache-Control "no-cache";
    }
    location = /manifest.webmanifest {
        default_type application/manifest+json;
        add_header Cache-Control "no-cache";
    }
    # Los assets llevan hash en el nombre: se pueden cachear un año.
    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
    # Rutas profundas (/lider/miembros) → index.html, como hacía el .htaccess
    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/espolclub /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Con el web en `/`, la raíz de Django (`GET /`, el índice JSON) deja de verse.
El índice del API sigue en `/api/v1/`.

> **Los PDFs se sirven por su URL.** Es el mismo comportamiento que en
> AlwaysData: el API devuelve la dirección de cada archivo y el servidor web la
> entrega sin pedir sesión. Un documento de club marcado como privado no
> aparece en los listados públicos, pero quien tenga su URL puede abrirlo.

### 5.3 HTTPS

```bash
sudo certbot --nginx -d TU-DOMINIO --redirect -m TU-CORREO --agree-tos -n
sudo systemctl list-timers | grep certbot     # renovación automática
```

Certbot añade el bloque `listen 443` y la redirección desde HTTP. Hasta este
paso, el API responde con redirecciones a HTTPS que todavía no funcionan: es lo
esperado.

---

## 6. Correo con Amazon SES

Sin correo nadie puede verificar su cuenta (RF-01) ni recuperar la contraseña
(RF-03). Los pasos 6.1 a 6.3 se ejecutan **en tu máquina**, con el AWS CLI.

### 6.1 Verificar el dominio

```bash
aws sesv2 create-email-identity --email-identity TU-DOMINIO \
  --query DkimAttributes.Tokens --output text
```

Devuelve tres tokens. Por cada uno, crea en tu registrador un **CNAME**:

```
<token>._domainkey.TU-DOMINIO  →  <token>.dkim.amazonses.com
```

```bash
# Repite hasta que diga SUCCESS (puede tardar hasta 72 h; suele ser menos de 1 h)
aws sesv2 get-email-identity --email-identity TU-DOMINIO \
  --query DkimAttributes.Status
```

### 6.2 Salir del sandbox

Una cuenta nueva de SES solo envía a direcciones verificadas una por una. Para
enviar a cualquier estudiante hay que pedir acceso de producción:

```bash
aws sesv2 put-account-details \
  --production-access-enabled \
  --mail-type TRANSACTIONAL \
  --website-url https://TU-DOMINIO \
  --contact-language EN \
  --use-case-description "Transactional email for ESPOLCLUB, the student clubs platform of ESPOL (Guayaquil, Ecuador): account verification and password reset links, only to students who sign up with their @espol.edu.ec address. No marketing. Bounces and complaints are monitored."

aws sesv2 get-account --query '{produccion:ProductionAccessEnabled,estado:Details.ReviewDetails.Status}'
```

AWS responde en uno o dos días. Mientras tanto, puedes probar verificando tu
propio correo: `aws sesv2 create-email-identity --email-identity TU-CORREO`.

### 6.3 Credenciales SMTP

Django envía por SMTP, así que necesita un usuario y una contraseña SMTP. Se
crean a partir de un usuario de IAM que solo puede enviar correo:

```bash
aws iam create-user --user-name espolclub-ses-smtp
aws iam put-user-policy --user-name espolclub-ses-smtp --policy-name ses-send \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"ses:SendRawEmail","Resource":"*"}]}'

read -r SMTP_USER SECRET_KEY < <(aws iam create-access-key --user-name espolclub-ses-smtp \
  --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)

# La contraseña SMTP se deriva de la clave secreta con el algoritmo que publica
# AWS (docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html)
SMTP_PASSWORD=$(SECRET_KEY="$SECRET_KEY" python3 - <<'PY'
import base64, hashlib, hmac, os
def sign(key, msg):
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()
sig = sign(("AWS4" + os.environ["SECRET_KEY"]).encode(), "11111111")
for part in ("us-east-1", "ses", "aws4_request", "SendRawEmail"):
    sig = sign(sig, part)
print(base64.b64encode(bytes([0x04]) + sig).decode())
PY
)
echo "EMAIL_HOST_USER=$SMTP_USER"
echo "EMAIL_HOST_PASSWORD=$SMTP_PASSWORD"
```

### 6.4 Cargarlas en el servidor

En el servidor, completa `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` en
`/srv/espolclub/api/.env` y reinicia:

```bash
sudo systemctl restart espolclub
```

Prueba: registra una cuenta desde el web y comprueba que llega el correo de
verificación.

---

## 7. Tareas programadas

```bash
sudo -u espolclub crontab - <<'EOF'
# Hora del sistema: America/Guayaquil (paso 3)
0  3 * * *  cd /srv/espolclub/api && /srv/espolclub/venv/bin/python manage.py freeze_expired_memberships >> /srv/espolclub/logs/cron.log 2>&1
15 3 * * *  cd /srv/espolclub/api && /srv/espolclub/venv/bin/python manage.py expire_stale_memberships >> /srv/espolclub/logs/cron.log 2>&1
5  * * * *  cd /srv/espolclub/api && /srv/espolclub/venv/bin/python manage.py expire_qr_tokens >> /srv/espolclub/logs/cron.log 2>&1
10 * * * *  cd /srv/espolclub/api && /srv/espolclub/venv/bin/python manage.py mark_no_shows >> /srv/espolclub/logs/cron.log 2>&1

# Volcado diario de la base (credenciales en ~/.my.cnf); se conservan 14 días
30 2 * * *  mysqldump --single-transaction espolclub | gzip > /srv/espolclub/backups/espolclub-$(date +\%F).sql.gz && find /srv/espolclub/backups -name '*.sql.gz' -mtime +14 -delete
EOF

sudo -u espolclub crontab -l
# Probar una sin cambiar nada:
sudo -u espolclub bash -c 'cd /srv/espolclub/api && /srv/espolclub/venv/bin/python manage.py freeze_expired_memberships --dry-run'
```

Los cuatro comandos son idempotentes; ver `DESPLIEGUE.md` §8 para qué hace cada
uno. El snapshot de Lightsail (paso 2.2) guarda la instancia entera; el
`mysqldump` permite recuperar solo la base, y conviene copiarlo de vez en cuando
fuera del servidor:

```bash
# En tu máquina
rsync -av -e "ssh -i ~/.ssh/espolclub-lightsail.pem" \
  ubuntu@"$IP":/srv/espolclub/backups/ ./backups-espolclub/
```

---

## 8. Publicar el cliente web

En **tu máquina**, desde `espol-club-web/`:

```bash
npm ci
# Mismo origen: el web pide /api/v1 a su propio dominio. La variable del
# entorno gana sobre la de .env.production, que apunta a AlwaysData.
VITE_API_BASE=/api/v1 npm run build

rsync -av --delete -e "ssh -i ~/.ssh/espolclub-lightsail.pem" \
  --rsync-path="sudo -u espolclub rsync" \
  dist/ ubuntu@"$IP":/srv/espolclub/web/
```

No hace falta reiniciar nada: nginx sirve los archivos nuevos al instante.

---

## 9. Actualizar

**API**, en el servidor:

```bash
cd /srv/espolclub/api
sudo -u espolclub git pull
sudo -u espolclub /srv/espolclub/venv/bin/pip install -r requirements.txt
sudo -u espolclub /srv/espolclub/venv/bin/python manage.py migrate
sudo -u espolclub /srv/espolclub/venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart espolclub
```

**Web**: repite el paso 8.

**Sistema**: `sudo apt update && sudo apt -y upgrade` una vez al mes, y reinicia
si lo pide. En AlwaysData esto lo hacía el proveedor; aquí es responsabilidad
de quien mantiene el servidor.

---

## 10. Comprobar que funciona

```bash
curl -s https://TU-DOMINIO/api/v1/catalogs/ | head -c 300   # 8 facultades y 8 áreas
curl -sI https://TU-DOMINIO/lider/miembros | head -1          # 200: la SPA atiende rutas profundas
curl -sI http://TU-DOMINIO/ | grep -i location                # redirige a https
```

Luego, en el navegador: abre `/admin/` (debe verse con estilos), inicia sesión
en el web y pide una recuperación de contraseña.

**Si algo falla:**

| Síntoma | Dónde mirar |
| :--- | :--- |
| 502 Bad Gateway | `sudo journalctl -u espolclub -n 50` (gunicorn no arrancó) |
| 500 en el API | `/srv/espolclub/logs/espolclub.log` |
| Bucle de redirecciones | Falta `proxy_set_header X-Forwarded-Proto` en nginx |
| 400 Bad Request | `DJANGO_ALLOWED_HOSTS` no coincide con el dominio |
| No llegan correos | `aws sesv2 get-account` (¿sigue en sandbox?) y el log de Django |
| Las tareas no corren | `/srv/espolclub/logs/cron.log` |

---

## 11. Lista de comprobación

- [ ] Presupuesto con alerta creado
- [ ] Instancia de 2 GB con IP estática y solo los puertos 22, 80 y 443
- [ ] Snapshots automáticos activados
- [ ] Dominio apuntando a la IP
- [ ] MariaDB 10.11 con colación `utf8mb4_uca1400_ai_ci`
- [ ] `check --deploy` sin avisos
- [ ] HTTPS activo y con renovación automática
- [ ] Dominio verificado en SES y acceso de producción aprobado
- [ ] Correo de verificación recibido
- [ ] Las cuatro tareas y el volcado de la base en el crontab
- [ ] Un PAO activo y un administrador GBP
- [ ] El web publicado y cargando desde el mismo dominio

## Volver atrás

Para borrar todo y dejar de pagar (desde tu máquina; **es irreversible**, haz
antes una copia de la base):

```bash
aws lightsail delete-instance --instance-name espolclub
aws lightsail release-static-ip --static-ip-name espolclub-ip
aws lightsail delete-key-pair --key-pair-name espolclub
# Los snapshots se borran aparte:
aws lightsail get-instance-snapshots --query 'instanceSnapshots[].name'
```
