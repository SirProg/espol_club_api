# ESPOLCLUB — Documento Maestro de Especificación

**Sistema:** ESPOLCLUB — Gestión de Clubes y Capítulos Estudiantiles de ESPOL
**Autor:** Kevin Maldonado Paredes
**Contexto:** Materia de Desarrollo Web (ESPOL)
**Licencia:** MIT
**Fecha de consolidación:** 2026-08-10
**Estado:** Fase 1 (Frontend con datos simulados) implementada. Documento preparado para construir la **Fase 2 con Django**.

---

## 0. Propósito y uso de este documento

Este archivo es la **única fuente de verdad portable** del proyecto. Consolida, sin depender de ningún otro archivo, todo lo que existe hoy en `README.md`, `requirements.md`, `frontend_design.md`, `pages_description.md`, los 12 `.json` de datos simulados y el código JavaScript de la Fase 1.

**Objetivo declarado:** poder llevar este `.md` a otro entorno de trabajo y, solo con él, construir el backend en **Django** (modelos, autenticación, permisos, reglas de negocio, endpoints, vistas y datos semilla) sin volver a leer el frontend.

**Cómo leerlo según lo que necesites:**

| Necesito… | Ir a |
| :--- | :--- |
| Entender el negocio | §1–§6 |
| Escribir `models.py` | §7 (modelo canónico) y §16.3 (traducción a Django) |
| Saber qué debe hacer el sistema | §8 y §9 (RF/RNF) |
| Saber qué pantallas existen y qué datos piden | §10–§13 |
| Escribir vistas/endpoints | §14 (contrato de operaciones) y §16.6 |
| Construir el proyecto Django completo | §16 (blueprint) |
| Cargar datos de prueba | §17 (fixtures) |
| Verificar cobertura de requerimientos | §19 (trazabilidad) |
| Saber qué está inconsistente hoy | §20 (divergencias) |

**Convención de idioma (regla transversal, RNF-10):** todo valor que viaja a la base de datos —especialmente las enumeraciones de estado— se escribe en **inglés** (`Pending`, `Active`, `Under Review`). La capa de presentación los traduce al **español** para el usuario final. El mapa de traducción canónico está en §18.

---

## Índice

1. [Visión general](#1-visión-general)
2. [Actores del sistema](#2-actores-del-sistema)
3. [Matriz de roles y permisos](#3-matriz-de-roles-y-permisos)
4. [Procesos principales del negocio](#4-procesos-principales-del-negocio)
5. [Máquinas de estado](#5-máquinas-de-estado)
6. [Reglas de negocio](#6-reglas-de-negocio)
7. [Modelo de datos canónico](#7-modelo-de-datos-canónico)
8. [Requerimientos funcionales](#8-requerimientos-funcionales)
9. [Requerimientos no funcionales](#9-requerimientos-no-funcionales)
10. [Inventario de pantallas](#10-inventario-de-pantallas)
11. [Mapa de navegación](#11-mapa-de-navegación)
12. [Formularios y validaciones](#12-formularios-y-validaciones)
13. [Elementos de visualización de datos](#13-elementos-de-visualización-de-datos)
14. [Contrato de operaciones (superficie funcional)](#14-contrato-de-operaciones-superficie-funcional)
15. [Arquitectura actual — Fase 1](#15-arquitectura-actual--fase-1)
16. [Arquitectura objetivo — Django](#16-arquitectura-objetivo--django)
17. [Datos semilla / fixtures](#17-datos-semilla--fixtures)
18. [Traducción de enumeraciones](#18-traducción-de-enumeraciones)
19. [Matriz de trazabilidad](#19-matriz-de-trazabilidad)
20. [Divergencias y deuda detectada](#20-divergencias-y-deuda-detectada)
21. [Preguntas pendientes de definición](#21-preguntas-pendientes-de-definición)
22. [Glosario](#22-glosario)

---

## 1. Visión general

### 1.1 El problema

ESPOLCLUB ataca la **fragmentación de información y de procesos** alrededor de los clubes y capítulos estudiantiles de ESPOL. Convierte un ecosistema informal y disperso en un **canal oficial, centralizado y trazable** que conecta tres mundos que hoy se comunican mal: la comunidad estudiantil, las directivas de los clubes y la Gerencia de Bienestar Politécnico (GBP).

Tres síntomas concretos:

- **Brecha de descubrimiento.** No existe un repositorio oficial y centralizado de clubes; el estudiante depende de redes sociales externas o de eventos presenciales puntuales (como la Novatada), lo que aísla a quien no usa esas plataformas.
- **Desconexión operativa.** La inscripción a clubes, el registro a eventos y el control de asistencia se llevan de forma manual y dispersa, perdiendo la trazabilidad de la participación estudiantil histórica.
- **Burocracia analógica con GBP.** La rendición de cuentas entre líderes e institución (nóminas, estatutos, reportes por PAO) carece de una vía estandarizada, ágil y auditable.

### 1.2 La solución

Un ecosistema digital con dos entornos:

- **Aplicación móvil (estudiantes):** catálogo dinámico y filtrable para descubrir comunidades, postular a membresías, inscribirse a eventos y portar una credencial QR.
- **Panel web administrativo (líderes y GBP):** entorno plano de gestión de datos donde las directivas configuran formularios, controlan accesos y generan la documentación requerida para su validación institucional.

### 1.3 Prioridades y núcleo irrenunciable

- **Prioridad de la primera versión:** el **descubrimiento**. Si los estudiantes no encuentran los clubes, lo demás no importa.
- **Núcleo irrenunciable:** que un estudiante pueda descubrir un club que no conocía y postular, y que ese club pueda demostrarle a GBP quiénes son sus miembros activos.

### 1.4 Stack y fases

| Fase | Alcance | Stack |
| :--- | :--- | :--- |
| **F1 — Frontend** | Interfaz completa e interactividad simulada | HTML5, Tailwind CSS (CDN), JavaScript ES6+ nativo, `.json` locales, `localStorage` |
| **F2 — Backend y persistencia** | Lógica de negocio real y base de datos | **Django + PostgreSQL** *(ver §16.1: cambio respecto de la definición original en FastAPI)* |
| **F3 — APIs REST** | Contratos diferenciados web/móvil | Django REST Framework |
| **F4 — App móvil** | Experiencia nativa del estudiante | React Native |

> **Nota de estado:** la Fase 1 está implementada y funcionando. Este documento existe para arrancar la Fase 2 en Django.

---

## 2. Actores del sistema

El sistema es **cerrado a la comunidad ESPOL**, con cuatro perfiles diferenciados por qué pueden ver y qué pueden hacer.

| Perfil | Entorno | Naturaleza |
| :--- | :--- | :--- |
| **Estudiante Politécnico** | App móvil | Comunidad — descubre, postula, se inscribe |
| **Miembro del Club** | App móvil | Comunidad — estudiante aceptado; puede ser Staff temporal |
| **Líder de Club** | Web / Móvil | Comunidad — directiva con poder administrativo sobre **un único** club |
| **Administrador GBP** | Panel web | Institución — audita y valida; no edita el interior de los clubes |

### Reglas de pertenencia confirmadas

- Un estudiante puede ser **miembro de varios clubes** simultáneamente.
- Un estudiante puede ser **líder de un club mientras es miembro de otro**, pero **líder de uno solo**.
- En GBP puede haber **varios administradores**, todos con el **mismo poder** (sin jerarquías internas en esta versión).
- La cuenta del estudiante **la crea él mismo** al registrarse con su correo institucional.
- Al graduarse o dejar ESPOL, la cuenta y sus membresías **caducan al cerrar el PAO** y no se renuevan; **no se borran** (quedan como histórico).
- El cargo del líder **no se guarda como texto libre**, sino mediante un `role_id` que apunta a la tabla de roles.

> **Fuera de alcance:** tutores docentes, coordinadores de facultad u otros actores institucionales.

---

## 3. Matriz de roles y permisos

### 3.1 Roles de aplicación (perfil de usuario)

| Rol | Entorno | Permisos clave | Restricciones críticas |
| :--- | :--- | :--- | :--- |
| **Estudiante Politécnico** | Móvil | Autenticación institucional; ver catálogo de clubes; aplicar a membresías y eventos | No ve la lista de miembros de un club (solo el contador); no accede al panel web |
| **Miembro del Club** | Móvil | Todo lo del estudiante + ver la nómina de **su** club + roles internos personalizados + (si es Staff) escanear QR del evento asignado | Su visualización interna se limita a los clubes a los que pertenece |
| **Líder de Club** | Web / Móvil | CRUD de eventos, información del club, miembros y roles; constructor de formularios; envío de reportes a GBP; asignación de roles y permisos | **Un (1) solo club** administrado |
| **Administrador GBP** | Web | Alta de clubes y asignación de líderes; recepción de documentos; aprobación/rechazo de reportes; descarga de reportería; configuración de PAO | **No edita** la información interna de los clubes: solo audita y valida |

### 3.2 Roles internos de club (tabla `Role`)

Cada club nace con **cuatro roles predeterminados** (`is_default: true`):

| Rol | `is_leadership` | Notas |
| :--- | :--- | :--- |
| Presidente/a | `true` | Todos los permisos activos. Único con `manage_roles` salvo delegación explícita |
| Vicepresidente/a | `true` | Sin `manage_roles`, sin `scan_event_qr`, sin `submit_gbp_reports` |
| Secretario/a | `true` | Solo `access_web_panel`, `manage_members`, `manage_documents` |
| Miembro | `false` | Rol base, **sin ningún permiso administrativo**. Se asigna por defecto al aprobar una solicitud |

Sobre esa base el Líder puede crear **roles personalizados** (`is_default: false`), por ejemplo *Encargado de Documentos* o *Staff de Eventos*.

### 3.3 Diccionario de permisos granulares

El bloque `permissions` es un **diccionario extensible**: agregar una capacidad nueva solo requiere añadir una clave; **una clave ausente se interpreta como `false`**.

| Clave | Significado |
| :--- | :--- |
| `access_web_panel` | Puede entrar al panel web del club |
| `manage_club_info` | Edita datos y documentos del club |
| `manage_members` | Administra la nómina (cambiar rol, dar de baja) |
| `manage_roles` | Crea roles y asigna permisos |
| `manage_forms` | Usa el constructor de formularios dinámicos |
| `manage_events` | Crea y edita eventos, asigna Staff |
| `scan_event_qr` | Escanea credenciales QR |
| `manage_documents` | Sube y clasifica documentos del club |
| `submit_gbp_reports` | Envía trámites a GBP |

---

## 4. Procesos principales del negocio

### A. Ciclo de creación de comunidades (GBP → Líder)

Un club **nunca nace por iniciativa del estudiante**: siempre lo origina GBP, que lo da de alta y vincula la **matrícula** de un estudiante, quien asciende a Líder.

1. GBP registra el club con nombre, acrónimo, descripción, ubicación, facultad, áreas de interés y matrícula del líder.
2. Si la matrícula **tiene cuenta**, el club queda `Active` y el estudiante recibe el rol Presidente/a.
3. Si la matrícula **no tiene cuenta**, el club queda `Pending Leader` y en **solo lectura**; el rol Presidente/a se activa automáticamente cuando esa matrícula completa su registro.

### B. Ciclo de membresía (Estudiante → Líder)

1. El Líder diseña un **formulario dinámico** de membresía en el panel web.
2. El estudiante postula desde la app llenando ese formulario.
3. La solicitud queda `Pending` y se enruta al panel del Líder.
4. El Líder **aprueba** (lo convierte en Miembro, creando una `Membership` activa con el rol Miembro) o **rechaza** con justificación obligatoria.

### C. Gestión de eventos y asistencia (flujo QR)

1. El Líder crea el evento y su formulario de registro.
2. El estudiante se inscribe y recibe una **credencial QR** (token opaco firmado por el servidor).
3. El Líder asigna miembros como **Staff de ese evento específico**.
4. Durante el evento, el Staff escanea para registrar asistencia real, **sin duplicados**.
5. El sistema calcula la métrica **Inscritos vs. Asistentes reales**.

### D. Rendición de cuentas (Líder → GBP)

1. El sistema consolida la nómina de miembros activos por PAO.
2. El Líder carga documentos (PDF) y envía el reporte, que queda `Submitted` y **congelado para edición**.
3. GBP lo abre (`Under Review`), lo audita y emite resolución `Approved` o `Rejected` (con feedback obligatorio, que reabre el trámite).
4. GBP puede exportar la información consolidada en `.xlsx` y `.pdf`.

### E. Descubrimiento y acceso a la información (transversal)

- Cualquier usuario autenticado puede explorar el catálogo de organizaciones.
- Los líderes controlan la privacidad de cada archivo subido: **público** para toda la comunidad o **privado** (exclusivo de los miembros del club).

---

## 5. Máquinas de estado

Los flujos del sistema se modelan como máquinas de estado explícitas. **No hay eliminación física de datos**: se usan cambios de estado y vigencias para preservar la trazabilidad.

### 5.1 Solicitud de membresía — `MembershipApplication.status`

```
        ┌──────────► Approved   (crea una Membership activa; registro congelado)
Pending ┤
        └──────────► Rejected   (exige leader_feedback; puede reenviarse de inmediato)
```

| Estado | Significado |
| :--- | :--- |
| `Pending` | Estado inicial al enviar el formulario desde la app |
| `Approved` | El Líder acepta. El registro se congela y **se genera una `Membership` activa** |
| `Rejected` | El Líder niega. `leader_feedback` pasa a ser obligatorio |

### 5.2 Membresía — `Membership.status`

```
Active ──(end_date del PAO)──► Frozen ──(no se renueva)──► Expired
   │                              │
   └──────────(revocación explícita)──────────► Revoked
```

| Estado | Significado |
| :--- | :--- |
| `Active` | Vigente dentro del PAO en curso; el estudiante goza de los permisos de su `role_id` |
| `Frozen` | Cierre del PAO. La nómina se congela como evidencia histórica auditable; el acceso operativo queda en pausa |
| `Expired` | Pasó `valid_until` y el Líder no renovó la nómina |
| `Revoked` | Revocación explícita (GBP retira el liderazgo, o el Líder da de baja a un miembro). Para roles directivos, libera la RN-1 |

### 5.3 Trámite GBP — `GbpDocumentProcess.status`

```
Submitted ──► Under Review ──┬──► Approved
                             └──► Rejected ──(reabre)──► el club vuelve a subir
```

### 5.4 Inscripción y credencial QR — `EventRegistration`

Dos campos de estado **independientes** sobre la misma fila:

```
attendance_status:  Registered ──► Attended        (QR validado)
                              └──► NoShow          (evento finalizado sin escaneo)

qr_status:          Active ──► Used                (ya validado; bloquea el reescaneo)
                          └──► Expired             (se alcanzó end_datetime del evento)
```

### 5.5 Club — `Club.status`

```
Pending Leader ──(la matrícula completa su registro / GBP asigna líder)──► Active
Active ──(GBP revoca al líder)──► Pending Leader   (club en solo lectura)
```

---

## 6. Reglas de negocio

Estas reglas son **obligación del backend**: deben validarse en código antes de procesar cualquier transacción, sin confiar en el cliente.

| ID | Regla | Detalle de implementación |
| :--- | :--- | :--- |
| **RN-1** | **Exclusividad de liderazgo** | Un Líder administra **un solo club** a la vez. Si deja el cargo, GBP revoca su acceso (`Membership.status = Revoked`) y asigna un nuevo líder. Validar que un `student_id` no tenga dos membresías `Active` con `role.is_leadership = true` en clubes distintos |
| **RN-2** | **Restricción de postulación activa** | Un estudiante no puede tener dos solicitudes `Pending` al mismo club, ni postular donde ya es miembro activo. Una solicitud **rechazada puede reenviarse inmediatamente**, sin tiempo de espera |
| **RN-3** | **Visualización por privacidad** | Los no-miembros solo ven métricas agregadas (ej. "45 miembros"). La nómina detallada (nombres, correos) es exclusiva de los miembros internos de ese club y de GBP |
| **RN-4** | **Caducidad por PAO** | Las membresías se **congelan automáticamente** al alcanzar la `end_date` del PAO. El Líder debe **renovar manualmente** la nómina al inicio del nuevo PAO |
| **RN-5** | **Feedback de rechazo obligatorio** | Rechazar una solicitud de membresía o un trámite GBP **exige** un campo de justificación no vacío. Aplica al Líder (`leader_feedback`) y a GBP (`review_feedback`) |
| **RN-6** | **No reescaneo de QR** | Un mismo QR no puede registrar asistencia dos veces. Se garantiza con la restricción `UNIQUE (event_id, student_id)` sobre `EventAttendance` y el cambio de `qr_status` a `Used` |
| **RN-7** | **Otorgamiento de permisos** | Solo roles con `is_leadership: true` pueden asignar roles/permisos; el permiso `manage_roles` queda restringido al **Presidente/a**, salvo delegación explícita |

### Flujos de control (operaciones permitidas)

- **Creación de comunidades:** un club solo existe si **GBP lo da de alta** y le vincula una matrícula.
- **Gestión unidireccional de formularios:** los formularios se diseñan, estructuran y modifican **exclusivamente** en el panel web por el Líder. La app móvil actúa **solo como cliente** que renderiza y envía respuestas.
- **Trazabilidad del flujo QR:** generación automática tras registro exitoso → escaneo por cuenta Staff autorizada → registro de asistencia único.

---

## 7. Modelo de datos canónico

Esta sección es **normativa** para el `models.py` de Django. Los nombres de campo aquí listados son los que usan los datos reales de la Fase 1 y los que deben conservarse (o mapearse explícitamente) en el backend.

### 7.1 Diagrama de relaciones

```
                    ┌─────────────┐
                    │  PaoPeriod  │◄──────────────────────┐
                    └──────┬──────┘                       │
                           │                              │
   ┌───────────┐    ┌──────▼──────────┐          ┌────────┴──────────┐
   │  Student  │◄───┤   Membership    ├─────────►│       Club        │
   │(enrollment│    │ (student,club,  │          │ (leader_enrollment│
   │  = clave  │    │  role, pao,     │          │  status, faculty, │
   │  natural) │    │  vigencia)      │          │  interest_areas)  │
   └─────┬─────┘    └────────┬────────┘          └───┬───────┬───────┘
         │                   │                       │       │
         │                   ▼                       │       │
         │            ┌────────────┐                 │       │
         │            │    Role    │◄────────────────┘       │
         │            │(permissions│                         │
         │            │   JSON)    │                         │
         │            └────────────┘                         │
         │                                                   │
         │   ┌──────────────────────┐        ┌───────────────▼──────┐
         ├──►│ MembershipApplication├───────►│        Form          │
         │   │  (responses JSON,    │  form  │ (fields JSON,        │
         │   │   status, feedback)  │        │  form_type, version) │
         │   └──────────────────────┘        └───────────▲──────────┘
         │                                               │
         │   ┌──────────────────────┐        ┌───────────┴──────────┐
         ├──►│  EventRegistration   ├───────►│        Event         │
         │   │ (qr_token, qr_status,│  event │ (visibility, stats,  │
         │   │  attendance_status)  │        │  deadlines)          │
         │   └──────────┬───────────┘        └───────────┬──────────┘
         │              │                                │
         │              ▼                                ▼
         │   ┌──────────────────────┐        ┌──────────────────────┐
         └──►│   EventAttendance    │        │     EventStaff       │
             │ UNIQUE(event,student)│        │ (asignación por      │
             │  scanned_by_staff    │        │  evento, N:M)        │
             └──────────────────────┘        └──────────────────────┘

   ┌──────────────────────┐        ┌──────────────────────┐
   │  GbpDocumentProcess  │───────►│         Club         │
   │ (pao, status, file,  │        └──────────────────────┘
   │  review_feedback)    │
   └──────────────────────┘

   ┌──────────────────────┐
   │    Notification      │───────► Student (user_id)
   │ (type, message, read)│
   └──────────────────────┘
```

### 7.2 Entidades

#### `Student` (Estudiante Politécnico)

La matrícula (`enrollment`) es el **identificador único institucional** (clave natural). La edad **no se almacena**: se deriva de `birth_date`. Las pertenencias a clubes **no se embeben aquí**: viven en `Membership`.

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `id` | int PK | no | Autoincremental |
| `enrollment` | str(20) | no | **UNIQUE**. Clave natural. Formato numérico (`202311346`) o institucional (`GBP-001`) |
| `first_name` | str(80) | no | |
| `last_name` | str(80) | no | |
| `birth_date` | date | sí | No puede ser futura. La edad se deriva |
| `email` | str | no | **UNIQUE**. Debe terminar en `@espol.edu.ec` |
| `semester` | int | sí | Entero positivo. Nulo para personal GBP |
| `faculty` | str(20) | sí | Del catálogo de facultades. Nulo para personal GBP |
| `career` | str(120) | sí | Nulo para personal GBP |
| `description` | text | sí | Editable por el propio estudiante |
| `skills` | array/JSON de str | sí | Editable por el propio estudiante |
| `social_media` | JSON `[{network, link}]` | sí | Editable. `link` debe ser URL válida |

**Ejemplo real:**
```json
{
  "id": 1, "enrollment": "202311346", "first_name": "Kevin", "last_name": "Maldonado",
  "birth_date": "2005-05-14", "email": "kmaldon@espol.edu.ec", "semester": 6,
  "faculty": "FIEC", "career": "Computación",
  "description": "Enfocado en data science y software libre.",
  "skills": ["Python", "React", "SQL"],
  "social_media": [{ "network": "GitHub", "link": "https://github.com/kmaldon" }]
}
```

#### `Club`

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `id` | int PK | no | |
| `name` | str(150) | no | Obligatorio para el alta |
| `acronym` | str(30) | no | Obligatorio |
| `description` | text | no | Obligatorio |
| `location` | str(120) | no | Obligatorio (ej. `FIEC 11D`) |
| `faculty` | str(20) | sí | Del catálogo. Alimenta el filtro del catálogo móvil |
| `interest_areas` | array de str | no | **≥1**, del catálogo cerrado de áreas |
| `image` | str | sí | Ruta relativa de la portada (ej. `assets/img/clubes/club_1.png`) |
| `leader_enrollment` | str(20) FK lógica → `Student.enrollment` | sí | Nulo cuando el líder fue revocado |
| `status` | enum | no | `Active` \| `Pending Leader` |
| `members_count` | int | no | Denormalizado. **En Django debe calcularse**, no almacenarse (ver §16.3) |
| `social_media` | JSON `[{network, link}]` | sí | |
| `internal_documents` | JSON `[{doc_id, title, file_url, is_public}]` | sí | Ver entidad `ClubDocument` |

#### `ClubDocument` (hoy embebido en `Club.internal_documents`)

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `doc_id` | int PK | no | |
| `club_id` | FK → `Club` | no | |
| `title` | str(150) | no | |
| `file_url` | str | no | **Solo `.pdf`** |
| `is_public` | bool | no | `true` = visible para toda la comunidad; `false` = solo miembros (RF-16) |

> **Decisión para Django:** promover este bloque a una tabla propia (`ClubDocument`) en vez de dejarlo como JSON embebido; el frontend ya lo trata como colección con identidad propia (`setDocVisibility(docId, …)`, `deleteClubDocument(docId)`).

#### `Role`

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `id` | int PK | no | |
| `club_id` | FK → `Club` | no | Los roles son **por club** |
| `role_name` | str(80) | no | **Único dentro del club** |
| `is_default` | bool | no | `true` para los 4 roles creados automáticamente; no se pueden borrar |
| `is_leadership` | bool | no | Solo estos pueden asignar roles/permisos (RN-7) |
| `permissions` | JSON `{clave: bool}` | no | Diccionario extensible; clave ausente = `false`. Ver §3.3 |

**Ejemplo de rol directivo:**
```json
{
  "id": 7, "club_id": 2, "role_name": "Presidente/a",
  "is_default": true, "is_leadership": true,
  "permissions": {
    "access_web_panel": true, "manage_club_info": true, "manage_members": true,
    "manage_roles": true, "manage_forms": true, "manage_events": true,
    "scan_event_qr": true, "manage_documents": true, "submit_gbp_reports": true
  }
}
```

#### `Membership`

Materializa la relación N:M *estudiante–club* con su rol y su vigencia por término académico. Da soporte directo a RN-1 y RN-4.

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `id` | int PK | no | |
| `student_id` | FK → `Student` | no | |
| `club_id` | FK → `Club` | no | |
| `role_id` | FK → `Role` | no | **Un solo `role_id` por membresía** (RF-09). El rol debe pertenecer al mismo club |
| `pao_period` | str(10) FK lógica → `PaoPeriod` | no | Ej. `2026-I` |
| `valid_from` | date | no | Copiado de `PaoPeriod.start_date` |
| `valid_until` | date | no | Copiado de `PaoPeriod.end_date` |
| `status` | enum | no | `Active` \| `Frozen` \| `Expired` \| `Revoked` |

**Restricción:** `UNIQUE (student_id, club_id, pao_period)` — un estudiante tiene como máximo una membresía por club y período.

#### `PaoPeriod` (Período Académico Ordinario)

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `pao_period` | str(10) PK | no | Identificador único (`2026-I`) |
| `start_date` | date | no | |
| `end_date` | date | no | **Posterior** a `start_date` |
| `status` | enum | no | `Active` \| `Closed`. **Solo uno puede estar `Active`**: activar uno cierra los demás |

#### `Form` (Formulario dinámico)

Modela el **esquema** que el Líder construye. La app móvil lo lee para renderizar; el backend lo usa para validar.

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `id` | int PK | no | |
| `club_id` | FK → `Club` | no | |
| `form_type` | enum | no | `Membership` \| `Event` |
| `event_id` | FK → `Event` | sí | Obligatorio si `form_type = Event`; nulo si `Membership` |
| `title` | str(150) | no | |
| `is_active` | bool | no | |
| `version` | int | no | `max(version del mismo club+tipo) + 1` |
| `fields` | JSON (ver abajo) | no | **≥1 campo** |

**Esquema de un campo (`fields[]`):**

| Clave | Tipo | Reglas |
| :--- | :--- | :--- |
| `field_id` | str | Estable; es la clave con la que se guardan las respuestas |
| `label` | str | Texto de la pregunta |
| `type` | enum | `text` \| `textarea` \| `number` \| `date` \| `select` \| `radio` \| `checkbox` |
| `required` | bool | |
| `order` | int | Orden de render |
| `options` | array de str | **≥2** si el tipo es `select`, `radio` o `checkbox`; vacío en el resto |
| `validation` | JSON | Ej. `{"max_length": 500}` |

**Versionado (RF-24):** un formulario con respuestas es **inmutable**. Editarlo genera una **nueva versión**; las respuestas existentes quedan ligadas a su versión original. Un formulario **sin** respuestas sí puede editarse en sitio.

#### `MembershipApplication` (Solicitud de membresía)

Guarda las **respuestas** referenciando `form_id` y cada `field_id`, no el texto de la pregunta (evita inconsistencias si el formulario cambia).

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `id` | int PK | no | |
| `student_id` | FK → `Student` | no | |
| `club_id` | FK → `Club` | no | |
| `form_id` | FK → `Form` | no | |
| `submitted_at` | datetime | no | Generado por el servidor |
| `responses` | JSON `[{field_id, answer}]` | no | |
| `status` | enum | no | `Pending` \| `Approved` \| `Rejected` |
| `leader_feedback` | text | sí | **Obligatorio si `status = Rejected`** (RN-5) |

#### `Event`

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `id` | int PK | no | |
| `club_id` | FK → `Club` | no | |
| `event_name` | str(150) | no | |
| `mode` | enum | no | `In-person` \| `Online` \| `Virtual` |
| `planned_date` | date | no | |
| `planned_hour` | time | no | |
| `end_datetime` | datetime | no | **Posterior** al inicio. Al alcanzarlo, los `qr_token` pasan a `Expired` |
| `planned_place` | str(150) | no | |
| `description` | text | sí | |
| `marketing_image` | str | sí | |
| `visibility` | enum | no | `Public` \| `MembersOnly` |
| `registration_form_id` | FK → `Form` | sí | Nulo = evento sin registro abierto |
| `registration_deadline` | datetime | sí | Debe ser **≤ inicio del evento** |
| `blocked_message` | str | sí | Mensaje personalizado del Líder cuando el registro está cerrado |
| `expected_participants` | int | sí | **Solo planificación**: no impone tope (RF-33) |
| `stats` | JSON `{registered, attended}` | — | **Derivado**: calcular, no almacenar (ver §16.3) |

**Datos administrativos opcionales** (documentados en el modelo original, no presentes en los datos de la Fase 1 — ver §20): `objective`, `sdg[]`, `responsible_member_id`, `responsible_task`, `allies`, `resource_links[]`, `impact_measure`.

#### `EventRegistration` (Inscripción a evento)

Representa al estudiante **ya inscrito y con credencial, pero aún sin asistir**. Es la fuente de la métrica *Inscritos vs. Asistentes* y la dueña del token QR.

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `id` | int PK | no | |
| `event_id` | FK → `Event` | no | |
| `student_id` | FK → `Student` | no | |
| `form_id` | FK → `Form` | no | |
| `registered_at` | datetime | no | Generado por el servidor |
| `responses` | JSON `[{field_id, answer}]` | no | |
| `qr_token` | str | no | **UNIQUE**. Token **opaco firmado por el servidor** |
| `qr_status` | enum | no | `Active` \| `Used` \| `Expired` |
| `attendance_status` | enum | no | `Registered` \| `Attended` \| `NoShow` |

**Restricción:** `UNIQUE (event_id, student_id)` — no se puede inscribir dos veces al mismo evento.

> **Diseño del QR (crítico, RNF-05):** el `qr_token` es un valor **opaco generado y firmado por el servidor**; no contiene `student_id` ni `event_id` legibles. El QR que ve el estudiante solo transporta ese token. Al escanear, el Staff envía el token al backend, que lo **valida contra la BD**: si es válido y `qr_status == "Active"`, registra la asistencia y marca el token como `Used`, impidiendo el reescaneo. Cualquier token alterado, ajeno o ya usado se rechaza.

#### `EventAttendance` (Asistencia)

Se crea **solo** al validar exitosamente el token. Sus datos son **inmutables al momento del escaneo** (RNF-12).

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `id` | int PK | no | |
| `registration_id` | FK → `EventRegistration` | no | Inscripción que originó la credencial validada |
| `event_id` | FK → `Event` | no | |
| `student_id` | FK → `Student` | no | |
| `scanned_at` | datetime | no | Timestamp con zona horaria, generado por el **servidor** |
| `scanned_by_staff_id` | FK → `Student` | sí | Trazabilidad de quién escaneó |
| `qr_token_validated` | str | no | Token efectivamente validado |
| `status` | enum | no | `Attended` |

**Restricción:** `UNIQUE (event_id, student_id)` — impide duplicados a nivel de base de datos (RN-6).

#### `EventStaff` (asignación de Staff por evento)

Hoy vive solo en el overlay del frontend; **debe existir como tabla** en el backend.

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `id` | int PK | no | |
| `event_id` | FK → `Event` | no | |
| `student_id` | FK → `Student` | no | Debe ser miembro **activo** del club del evento |

**Restricción:** `UNIQUE (event_id, student_id)`.

> **Decisión de diseño:** el Staff es una **asignación por evento**, no un permiso de rol permanente. El escaneo es válido **solo durante ese evento**. Los permisos nacen y mueren con el evento asociado.

#### `GbpDocumentProcess` (Trámite ante GBP)

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `id` | int PK | no | |
| `club_id` | FK → `Club` | no | |
| `pao_period` | str(10) FK lógica → `PaoPeriod` | no | |
| `document_type` | str(120) | no | Ej. `Nómina de Miembros` |
| `file_url` | str | no | **Solo `.pdf`** |
| `uploaded_at` | datetime | no | |
| `status` | enum | no | `Submitted` \| `Under Review` \| `Approved` \| `Rejected` |
| `review_feedback` | text | sí | **Obligatorio si `status = Rejected`** (RN-5) |
| `reviewed_by_gbp_id` | FK → `Student` | sí | Administrador GBP que resolvió |

**Regla:** una vez `Submitted`, el club **no puede editarlo**. Un `Rejected` reabre la posibilidad de subir un archivo corregido.

#### `Notification`

| Campo | Tipo | Nulo | Reglas |
| :--- | :--- | :--- | :--- |
| `id` | int PK | no | |
| `user_id` | FK → `Student` | no | Destinatario |
| `type` | str(60) | no | `application_pending`, `application_rejected`, `application_approved`, `event_registered`, `gbp_review`, … |
| `message` | text | no | |
| `date` | datetime | no | |
| `read` | bool | no | Se marca al abrir el centro de notificaciones |

### 7.3 Catálogos cerrados

| Catálogo | Valores |
| :--- | :--- |
| **Facultades** *(provisional, ver PPD-01)* | FIEC, FCNM, FIMCP, FICT, FCSH, FCV, FADCOM |
| **Áreas de interés** *(catálogo cerrado)* | Tecnología, Ciencia, Cultura, Deporte, Emprendimiento, Social, Arte, Académico |
| **Tipos de campo de formulario** | `text`, `textarea`, `number`, `date`, `select`, `radio`, `checkbox` |
| **Formatos de archivo permitidos** | `.xlsx` (datos tabulares), `.pdf` (texto). **Sin soporte** para `.doc`/`.docx` |

### 7.4 Resumen de restricciones de integridad

| # | Restricción | Entidad | Regla asociada |
| :--- | :--- | :--- | :--- |
| 1 | `UNIQUE (enrollment)` | `Student` | RF-05 |
| 2 | `UNIQUE (email)` | `Student` | RF-01 |
| 3 | `UNIQUE (event_id, student_id)` | `EventAttendance` | RN-6 / RF-36 |
| 4 | `UNIQUE (event_id, student_id)` | `EventRegistration` | Evita doble inscripción |
| 5 | `UNIQUE (qr_token)` | `EventRegistration` | RNF-05 |
| 6 | `UNIQUE (student_id, club_id, pao_period)` | `Membership` | Una membresía por club y período |
| 7 | `UNIQUE (club_id, role_name)` | `Role` | Nombre de rol único por club |
| 8 | Un solo `PaoPeriod` con `status = Active` | `PaoPeriod` | RF-45 |
| 9 | Máximo una `Membership` `Active` con rol `is_leadership` por estudiante | `Membership` | RN-1 |
| 10 | `leader_feedback` no vacío si `status = Rejected` | `MembershipApplication` | RN-5 |
| 11 | `review_feedback` no vacío si `status = Rejected` | `GbpDocumentProcess` | RN-5 |
| 12 | `role.club_id == membership.club_id` | `Membership` | RF-09 |
| 13 | `end_date > start_date` | `PaoPeriod` | F-19 |
| 14 | `end_datetime > planned_date + planned_hour` | `Event` | F-13 |
| 15 | `registration_deadline <= inicio del evento` | `Event` | F-13 |

---

## 8. Requerimientos funcionales

**57 requerimientos.** Los marcados con 🔒 son responsabilidad **primaria del backend** (Django).

### Autenticación y cuentas

| ID | Requerimiento |
| :--- | :--- |
| **RF-01** | Permitir el registro únicamente con correo institucional `@espol.edu.ec`, validado mediante enlace de verificación |
| **RF-02** | Permitir el inicio de sesión mediante contraseña propia del sistema |
| **RF-03** | Ofrecer recuperación de contraseña por correo |
| **RF-04** | En la Fase 1, simular el inicio de sesión con cuatro usuarios mock, uno por rol |
| **RF-05** 🔒 | Impedir el registro de dos cuentas con la misma matrícula (`enrollment`) |

### Roles y permisos

| ID | Requerimiento |
| :--- | :--- |
| **RF-06** 🔒 | Crear automáticamente, en cada club, cuatro roles predeterminados: Presidente/a, Vicepresidente/a, Secretario/a y Miembro |
| **RF-07** | Permitir al Líder crear roles personalizados y asignarles permisos granulares |
| **RF-08** 🔒 | Asignar el rol Miembro por defecto al crear una membresía tras aprobar una solicitud |
| **RF-09** 🔒 | Permitir un único `role_id` por membresía dentro de un mismo club |
| **RF-10** | Permitir asignar roles/permisos solo a roles con `is_leadership: true`, restringiendo `manage_roles` al Presidente/a salvo delegación explícita |

### Ciclo de vida del club

| ID | Requerimiento |
| :--- | :--- |
| **RF-11** | Permitir que únicamente GBP dé de alta un club y asigne un líder vinculando una matrícula |
| **RF-12** 🔒 | Dejar el club en `Pending Leader` cuando la matrícula asignada no tiene cuenta, y activar el Presidente/a automáticamente al completarse el registro |
| **RF-13** 🔒 | Al revocar a un líder, pasar su membresía directiva a `Revoked`, poner el club en `Pending Leader` y mantenerlo en solo lectura hasta nueva asignación |
| **RF-14** | Exigir, para registrar un club, nombre, acrónimo, descripción, ubicación, líder asignado y documentos formales |
| **RF-15** | Capturar en el club el campo `interest_areas` a partir de un catálogo cerrado |
| **RF-16** | Permitir al Líder definir cada documento del club como público o privado |

### Membresías y vigencia

| ID | Requerimiento |
| :--- | :--- |
| **RF-17** 🔒 | Permitir que un estudiante sea miembro de varios clubes simultáneamente, pero líder de uno solo |
| **RF-18** 🔒 | Registrar en cada membresía su `pao_period`, `valid_from` y `valid_until` |
| **RF-19** 🔒 | Gestionar los estados de membresía: `Active`, `Frozen`, `Expired`, `Revoked` |
| **RF-20** 🔒 | Congelar automáticamente las membresías vigentes al alcanzar la `end_date` del PAO |
| **RF-21** 🔒 | Permitir la renovación manual de la nómina por parte del Líder al inicio del nuevo PAO |

### Formularios dinámicos

| ID | Requerimiento |
| :--- | :--- |
| **RF-22** | Permitir al Líder construir, desde la web, formularios dinámicos de membresía y de evento |
| **RF-23** | Permitir que la app móvil renderice y envíe respuestas de dichos formularios, actuando solo como cliente |
| **RF-24** 🔒 | Tratar como inmutable un formulario con respuestas, generando una nueva versión al editarlo y conservando las respuestas en su versión original |

### Solicitudes de membresía

| ID | Requerimiento |
| :--- | :--- |
| **RF-25** | Permitir al estudiante postular a un club desde la app móvil llenando el formulario dinámico |
| **RF-26** | Enrutar la solicitud al panel web del Líder en estado `Pending` |
| **RF-27** | Permitir al Líder aprobar o rechazar la solicitud, exigiendo retroalimentación obligatoria en el rechazo |
| **RF-28** 🔒 | Impedir más de una solicitud `Pending` al mismo club o postular donde ya es miembro |
| **RF-29** 🔒 | Permitir reenviar inmediatamente una solicitud rechazada, sin tiempo de espera |

### Eventos y asistencia (QR)

| ID | Requerimiento |
| :--- | :--- |
| **RF-30** | Permitir al Líder crear un evento con sus datos de planificación, su `end_datetime` y la fecha límite de registro |
| **RF-31** | Manejar la `visibility` del evento (`Public`/`MembersOnly`); los `MembersOnly` son **visibles** pero con formulario bloqueado para no-miembros |
| **RF-32** | Permitir al estudiante inscribirse a un evento desde la app móvil, generando una inscripción y un `qr_token` opaco firmado |
| **RF-33** 🔒 | Permitir inscripciones sin tope; `expected_participants` es solo planificación |
| **RF-34** | Bloquear el registro al exceder la fecha límite, mostrando el mensaje personalizado del Líder |
| **RF-35** | Permitir al Líder asignar miembros como Staff de un evento específico, habilitando el escaneo solo durante ese evento |
| **RF-36** 🔒 | Registrar la asistencia validando el `qr_token` contra la BD e impedir duplicados por reescaneo mediante unicidad `(evento, estudiante)` |
| **RF-37** 🔒 | Marcar el `qr_token` como `Expired` automáticamente al alcanzar el `end_datetime` |
| **RF-38** | Calcular y mostrar la métrica de inscritos vs. asistentes reales por evento |

### Rendición de cuentas (GBP)

| ID | Requerimiento |
| :--- | :--- |
| **RF-39** 🔒 | Consolidar la nómina de miembros activos por PAO |
| **RF-40** | Permitir al Líder cargar documentos en PDF y enviar los reportes generados |
| **RF-41** 🔒 | Congelar el reporte enviado, bloqueándolo para edición mientras está en revisión |
| **RF-42** | Permitir a GBP visualizar los datos estructurados y exportarlos en `.xlsx` y `.pdf` |
| **RF-43** | Permitir a GBP emitir una resolución `Approved`/`Rejected`, exigiendo feedback en el rechazo y reabriendo el trámite |
| **RF-44** 🔒 | Gestionar los estados del trámite: `Submitted`, `Under Review`, `Approved`, `Rejected` |

### Configuración de PAO

| ID | Requerimiento |
| :--- | :--- |
| **RF-45** | Permitir a GBP administrar la configuración del PAO (`pao_period`, `start_date`, `end_date`) |

### Consulta y visibilidad

| ID | Requerimiento |
| :--- | :--- |
| **RF-46** | Ofrecer un catálogo de clubes filtrable por texto (nombre/acrónimo), facultad y área de interés |
| **RF-47** | Mostrar a no-miembros únicamente el contador numérico de miembros, ocultando identidades |
| **RF-48** | Mostrar la nómina detallada solo a miembros internos del club y a GBP |
| **RF-49** | Permitir consultar información histórica por PAO (clubes y líderes de semestres anteriores) |
| **RF-50** | Permitir al estudiante visualizar/editar sus datos y consultar su historial de postulaciones y asistencias |

### Notificaciones y trazabilidad

| ID | Requerimiento |
| :--- | :--- |
| **RF-51** | Contar con un centro de notificaciones in-app, en web y móvil, para cambios de estado de solicitudes, reportes y membresías |
| **RF-52** 🔒 | Registrar como auditables las acciones del Líder (quién aprobó/rechazó y cuándo) |

### Distribución de acciones web/móvil

| ID | Requerimiento |
| :--- | :--- |
| **RF-53** | Permitir exclusivamente desde la web la construcción de formularios, la gestión de miembros/roles y el envío de documentación a GBP |
| **RF-54** | Permitir al Administrador GBP operar únicamente desde la web |
| **RF-55** | Permitir al estudiante, desde la app móvil, explorar el catálogo, postular, inscribirse a eventos, ver su QR y consultar su historial |
| **RF-56** | Permitir al Staff escanear códigos QR desde la app móvil |
| **RF-57** | Permitir al Líder aprobar solicitudes desde la app móvil como conveniencia |

---

## 9. Requerimientos no funcionales

| ID | Requerimiento |
| :--- | :--- |
| **RNF-01** | Operar en dos entornos: panel web administrativo y aplicación móvil para estudiantes |
| **RNF-02** | En la Fase 1, el frontend debe funcionar con datos simulados (`.json` locales), sin build, usando Tailwind CSS vía CDN |
| **RNF-03** | Desarrollarse progresivamente en cuatro fases: (1) frontend, (2) backend con base de datos relacional, (3) APIs REST, (4) app móvil en React Native |
| **RNF-04** | Implementar autenticación y autorización mediante JWT a partir de la Fase 2 |
| **RNF-05** | El código QR debe basarse en un token opaco firmado por el servidor, verificable solo contra la BD |
| **RNF-06** | Proteger la privacidad de los datos personales de los miembros, con información diferenciada entre móvil (oculta identidades) y web (las expone a roles autorizados) |
| **RNF-07** | El panel web debe ser plano (tablas, formularios, botones), sin dashboards analíticos, gráficos dinámicos ni animaciones avanzadas |
| **RNF-08** | Limitar la documentación a `.xlsx` (datos tabulares) y `.pdf` (texto), sin `.doc`/`.docx` |
| **RNF-09** | No integrarse con el SAAC ni otros sistemas centrales de ESPOL; la verificación se apoya en el correo institucional y los datos declarados |
| **RNF-10** | Usar enumeraciones en inglés a nivel de BD y su traducción al español en la presentación |
| **RNF-11** | La app móvil debe requerir acceso a la cámara para el escaneo de QR; no exige modo totalmente offline |
| **RNF-12** | Los registros de asistencia deben ser inmutables al momento del escaneo |
| **RNF-13** | El proyecto se distribuye bajo Licencia MIT |

---

## 10. Inventario de pantallas

**34 pantallas:** 5 compartidas (auth), 11 móviles, 12 del panel del Líder y 6 del panel de GBP.

### A. Compartidas (autenticación — web y móvil)

| # | Pantalla | Usuario | Objetivo |
| :-- | :--- | :--- | :--- |
| 1 | Inicio de sesión | Todos | Acceso según rol |
| 2 | Registro de cuenta | Estudiante | Crear cuenta con correo institucional |
| 3 | Verificación de correo | Estudiante | Confirmar la cuenta vía enlace |
| 4 | Recuperación de contraseña | Todos | Restablecer acceso |
| 5 | Centro de notificaciones | Todos | Cambios de estado de solicitudes, reportes, membresías |

> La pantalla 5 **no tiene página propia**: se implementa como una campana desplegable en la cabecera compartida, disponible en los tres entornos.

### B. Entorno móvil (Estudiante / Miembro)

| # | Pantalla | Objetivo principal | Acciones |
| :-- | :--- | :--- | :--- |
| 6 | Catálogo de clubes | Descubrir clubes (eje prioritario) | Buscar, filtrar, abrir detalle |
| 7 | Detalle de club | Ver info del club (pública o interna) | Postular, ir a eventos |
| 8 | Formulario de postulación | Enviar solicitud de membresía | Responder y enviar |
| 9 | Eventos disponibles | Mostrar eventos inscribibles | Abrir detalle |
| 10 | Detalle de evento | Ver evento y disponibilidad de registro | Iniciar inscripción |
| 11 | Formulario de inscripción a evento | Registrar participación y generar QR | Responder y confirmar |
| 12 | Credencial QR | Portar la credencial de acceso | Visualizar |
| 13 | Escáner QR (Staff) | Validar y registrar asistencia | Escanear |
| 14 | Perfil del estudiante | Gestionar datos propios | Ver y editar |
| 15 | Historial personal | Consultar postulaciones y asistencias | Consultar, abrir detalle |
| 16 | Bandeja de solicitudes (móvil) | Aprobar solicitudes (conveniencia del Líder) | Aprobar / rechazar |

### C. Entorno web — Panel del Líder

| # | Pantalla | Objetivo principal | Acciones |
| :-- | :--- | :--- | :--- |
| 17 | Panel del club | Entrada plana a la gestión | Navegar a módulos, ver métricas |
| 18 | Información del club | Mantener datos y documentos | Editar, cargar PDF, definir visibilidad |
| 19 | Gestión de miembros / nómina | Administrar la nómina detallada | Ver, asignar rol, dar de baja |
| 20 | Roles y permisos | Configurar roles del club | Crear roles, asignar permisos |
| 21 | Bandeja de solicitudes | Resolver postulaciones | Aprobar / rechazar con feedback |
| 22 | Constructor de formularios | Diseñar formularios dinámicos | Crear, estructurar, versionar |
| 23 | Gestión de eventos | Histórico y desempeño de eventos | Crear, abrir detalle, asignar Staff |
| 24 | Creación / edición de evento | Definir evento y su registro | Crear / editar |
| 25 | Asignación de Staff | Habilitar escaneo por evento | Asignar / retirar Staff |
| 26 | Renovación de nómina por PAO | Reactivar la nómina del nuevo PAO | Renovar |
| 27 | Rendición de cuentas a GBP | Enviar reportes y documentos | Cargar PDF, enviar reporte |
| **34** | **Bitácora del club** | **Registro de inscritos por evento** | **Consultar** |

> **Pantalla 34 (Bitácora):** añadida después de la consolidación original de 33 pantallas. Lista, para un evento del club, los inscritos con nombre, apellido, matrícula y fecha de registro. **Estado actual:** implementada de forma mínima, muestra solo el **primer evento** del club sin selector. Ver §20.

### D. Entorno web — Panel de GBP

| # | Pantalla | Objetivo principal | Acciones |
| :-- | :--- | :--- | :--- |
| 28 | Catálogo global de clubes | Supervisar clubes activos | Buscar, abrir detalle, ver histórico |
| 29 | Alta de club y asignación de líder | Crear clubes y vincular líder | Dar de alta |
| 30 | Detalle de club (GBP) | Auditar y gestionar liderazgo | Revocar / asignar líder |
| 31 | Buzón de trámites | Auditar y resolver documentación | Abrir PDF, aprobar/rechazar, exportar |
| 32 | Configuración de PAO | Administrar calendario académico | Crear / editar períodos |
| 33 | Histórico por PAO | Revisar evidencia de semestres pasados | Seleccionar PAO y consultar |

### Clasificación por operación

- **Registran información:** 2, 8, 11, 13, 18, 20, 22, 24, 25, 27, 29, 32.
- **Consultan información:** 5, 6, 7, 9, 10, 12, 15, 16, 19, 21, 23, 28, 30, 31, 33, 34.
- **Editan / cambian estado:** 14, 18, 20, 22, 24, 32 (edición); 16, 21, 25, 26, 30, 31 (cambio de estado / baja lógica).

> **No hay eliminación física de datos:** se usan cambios de estado y vigencias (`Revoked`, `Frozen`, `Expired`) para preservar la trazabilidad (RF-52, RNF-12).

---

## 11. Mapa de navegación

### Enrutamiento por rol

La **pantalla inicial es Inicio de sesión (1)**, único punto de entrada. Actúa como enrutador: según el rol autenticado lleva a uno de tres "hogares". Los flujos de **Registro (2) → Verificación (3)** y **Recuperación (4)** siempre regresan al login.

```
                 Registro (2) → Verificación (3)
                                      │
                                      ▼
   Recuperación (4) ───────────►  Inicio de sesión (1)
                                      │  (enruta por rol)
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
     Catálogo de clubes (6)    Panel del club (17)     Catálogo global (28)
     Móvil (estudiante)        Web (líder)             Web (GBP)
```

**Mapa rol → hogar:**

| Rol | Hogar |
| :--- | :--- |
| Estudiante Politécnico | Catálogo de clubes (6) |
| Miembro del Club | Catálogo de clubes (6) |
| Líder de Club | Panel del club (17) |
| Administrador GBP | Catálogo global (28) |

### Menú principal por entorno

- **Móvil (Estudiante / Miembro):** Clubes · Eventos · Mi credencial QR · Perfil · Historial · Notificaciones. *(El Miembro ve además Escáner QR; el Líder ve además su Bandeja móvil.)*
- **Web del Líder:** Panel · Información · Miembros · Roles · Solicitudes · Formularios · Eventos · Nómina PAO · Rendición · **Bitácora** · Notificaciones.
- **Web de GBP:** Catálogo · Alta de club · Buzón de trámites · Configuración de PAO · Histórico · Notificaciones.

### Navegación interna

- **Móvil:** 6 → 7 → 8 · 9 → 10 → 11 → 12 · 13 (solo Staff) · 14 · 15 · 16 (solo Líder).
- **Web Líder:** 17 → 18 · 19 ↔ 20 · 21 · 22 · 23 → 24 → 25 · 26 · 27 · 34.
- **Web GBP:** 28 → 29 · 30 · 31 · 32 · 33.

### Flujo básico por rol

- **Estudiante:** Login → Catálogo (6) → Detalle (7) → Postula (8) → notificación (5) → Eventos (9) → Detalle (10) → Inscripción (11) → Credencial QR (12). Edita Perfil (14) y revisa Historial (15).
- **Staff:** Login → Escáner QR (13) → valida asistencias durante el evento.
- **Líder:** Login → Panel (17) → resuelve Solicitudes (21), diseña Formularios (22), crea Eventos (24) y asigna Staff (25), renueva nómina (26), envía Rendición (27), consulta Bitácora (34).
- **GBP:** Login → Catálogo global (28) → Alta (29), audita en Detalle (30) y Buzón (31), administra PAO (32), consulta Histórico (33).

---

## 12. Formularios y validaciones

**19 formularios.** Los de postulación (F-05) e inscripción (F-06) son **dinámicos**: envoltorio fijo + cuerpo de campos construido por el Líder (F-12). Todos los formularios de rechazo comparten la regla de **feedback obligatorio** (RN-5).

> **Nota para Django:** estas validaciones son *de cliente*. Toda validación aquí listada **debe replicarse en el servidor** (serializers / `clean()`), porque el cliente es no confiable.

### A. Autenticación

| ID | Pantalla | Campos clave | Validaciones |
| :-- | :--- | :--- | :--- |
| F-01 | Login (1) | matrícula/correo, contraseña | Obligatorios; formato de correo |
| F-02 | Registro (2) | matrícula, nombres, apellidos, fecha nac., correo, facultad, carrera, semestre, contraseña×2 | Correo `@espol.edu.ec`; semestre entero positivo; fecha no futura; contraseñas coinciden; matrícula única |
| F-03 | Recuperación (4) | correo institucional | Obligatorio; formato `@espol.edu.ec` |

### B. Entorno móvil

| ID | Pantalla | Campos clave | Validaciones |
| :-- | :--- | :--- | :--- |
| F-04 | Catálogo (6) | búsqueda texto, facultad, área de interés | Ninguno obligatorio; selects del catálogo |
| F-05 | Postulación (8) *(dinámico)* | cuerpo dinámico según esquema | `required` del esquema; bloqueo si ya hay `Pending` o ya es miembro (RN-2) |
| F-06 | Inscripción evento (11) *(dinámico)* | cuerpo dinámico según esquema | `required`; bloqueo por fecha límite, por `MembersOnly` o por inscripción previa |
| F-07 | Perfil (14) | descripción, habilidades, redes | URLs válidas; longitud máxima |
| F-08 | Bandeja móvil (16) | decisión (aprobar/rechazar), feedback | Feedback obligatorio al rechazar |

### C. Panel del Líder

| ID | Pantalla | Campos clave | Validaciones |
| :-- | :--- | :--- | :--- |
| F-09 | Información del club (18) | nombre, acrónimo, descripción, ubicación, áreas, redes, documento PDF + visibilidad | Obligatorios; ≥1 área; archivo `.pdf`; URLs válidas |
| F-10 | Roles (20) | nombre del rol, checkboxes de permisos | Nombre único en el club; `manage_roles` solo Presidente/delegado (RN-7) |
| F-11 | Solicitudes (21) | decisión, feedback | Feedback obligatorio al rechazar |
| F-12 | Constructor de formularios (22) | título, tipo; por campo: etiqueta, tipo, obligatorio, opciones, orden | Título y ≥1 campo; `select`/`radio`/`checkbox` exigen ≥2 opciones; aviso de nueva versión si hay respuestas |
| F-13 | Crear/editar evento (24) | nombre, modalidad, fecha, hora, `end_datetime`, lugar, descripción, imagen, visibilidad, fecha límite, mensaje de bloqueo, participantes, formulario | Fin posterior al inicio; límite ≤ inicio; imagen válida |
| F-14 | Asignación de Staff (25) | miembros (multiselección) | Solo miembros activos del club |
| F-15 | Renovación de nómina (26) | PAO, miembros a mantener | PAO requerido; ≥1 miembro |
| F-16 | Rendición de cuentas (27) | PAO, tipo de documento, archivo PDF | PAO y tipo obligatorios; archivo `.pdf` |

### D. Panel de GBP

| ID | Pantalla | Campos clave | Validaciones |
| :-- | :--- | :--- | :--- |
| F-17 | Alta de club (29) | nombre, acrónimo, descripción, ubicación, facultad, áreas, matrícula del líder | Obligatorios; ≥1 área; aviso si la matrícula no tiene cuenta (`Pending Leader`) |
| F-18 | Buzón de trámites (31) | decisión, feedback; exportar `.xlsx`/`.pdf` | Feedback obligatorio al rechazar |
| F-19 | Configuración de PAO (32) | identificador, fecha inicio, fecha fin | Fin posterior al inicio; identificador único |

### Patrón de mensajes

| Situación | Patrón | Ejemplo |
| :--- | :--- | :--- |
| Error de validación | Mensaje específico junto al campo | "El correo debe ser institucional (@espol.edu.ec)" |
| Bloqueo por regla | Mensaje contextual | "Ya tienes una solicitud pendiente en este club" · "El registro está cerrado" |
| Confirmación | Mensaje de éxito tras enviar | "Solicitud enviada. Te notificaremos la respuesta" |

### Mensajes de bloqueo canónicos (del código actual)

| Situación | Mensaje |
| :--- | :--- |
| Ya es miembro | `Ya eres miembro activo de este club.` |
| Solicitud pendiente | `Ya tienes una solicitud pendiente en este club.` |
| Ya inscrito al evento | `Ya estás inscrito en este evento.` |
| Evento sin registro | `Este evento no tiene registro abierto.` |
| Evento solo miembros | `blocked_message` del evento, o `Evento exclusivo para miembros.` |
| Fecha límite excedida | `blocked_message` del evento, o `El registro está cerrado.` |
| QR vacío | `Ingresa o escanea un código.` |
| QR desconocido | `Credencial no reconocida.` |
| QR ya usado | `Esta credencial ya registró asistencia.` |
| QR válido | `Asistencia registrada correctamente.` |

---

## 13. Elementos de visualización de datos

**25 elementos.** Criterio de tipo: **tarjetas** para descubrimiento, **tablas** para gestión/auditoría, **paneles** para detalle de una entidad, **listas** para flujos secuenciales.

### A. Entorno móvil

| ID | Pantalla | Tipo | Datos · Estado vacío |
| :-- | :--- | :--- | :--- |
| V-01 | Catálogo (6) | Tarjetas | Club + **solo contador** de miembros · "No se encontraron clubes con esos filtros" |
| V-02 | Detalle club / no miembro (7) | Panel | Info + documentos públicos + conteo · "Este club aún no ha publicado información" |
| V-03 | Detalle club / miembro (7) | Lista | Nómina interna + documentos privados · "Aún no hay miembros registrados" |
| V-04 | Eventos disponibles (9) | Tarjetas | Post de evento; etiqueta `MembersOnly` · "No hay eventos disponibles por ahora" |
| V-05 | Detalle de evento (10) | Panel | Evento + estado de registro · muestra el mensaje del Líder si está cerrado |
| V-06 | Credencial QR (12) | Tarjeta-credencial | QR + datos del evento · "Aún no tienes credenciales" |
| V-07 | Escáner QR (13) | Panel de confirmación | Resultado de validación · estado inicial "Apunta la cámara al QR" |
| V-08 | Historial (15) | Lista (2 secciones) | Postulaciones + asistencias · "Todavía no registras postulaciones ni asistencias" |
| V-09 | Perfil (14) | Sección/panel | Datos solo lectura + editables · siempre existe |

### B. Transversal

| ID | Pantalla | Tipo | Datos · Estado vacío |
| :-- | :--- | :--- | :--- |
| V-10 | Notificaciones (5) | Lista | Notificaciones con tipo/fecha/leído · "No tienes notificaciones" |
| V-11 | Bandeja móvil (16) | Lista | Solicitudes `Pending` + respuestas · "No hay solicitudes pendientes" |

### C. Panel del Líder

| ID | Pantalla | Tipo | Datos · Estado vacío |
| :-- | :--- | :--- | :--- |
| V-12 | Panel del club (17) | Panel | Estado + accesos + métricas · aviso si `Pending Leader` |
| V-13 | Miembros (19) | Tabla | Nómina detallada + rol + vigencia · "Este club aún no tiene miembros" |
| V-14 | Roles (20) | Tabla | 4 predeterminados + personalizados + permisos · siempre existen los 4 |
| V-15 | Solicitudes (21) | Tabla/lista | `Pending` + respuestas dinámicas · "No hay solicitudes pendientes" |
| V-16 | Constructor (22) | Panel/lista | Campos añadidos + versión activa · "Aún no has añadido campos" |
| V-17 | Eventos (23) | Tabla | Eventos + **inscritos vs. asistentes** · "Este club aún no ha creado eventos" |
| V-18 | Staff (25) | Lista | Disponibles vs. asignados · "No hay miembros disponibles para asignar" |
| V-19 | Renovación PAO (26) | Tabla con selección | Nómina congelada + vigencia · "No hay nómina previa para renovar" |
| V-20 | Rendición (27) | Tabla | Nómina consolidada + estado de trámites · "Aún no has enviado reportes a GBP" |

### D. Panel de GBP

| ID | Pantalla | Tipo | Datos · Estado vacío |
| :-- | :--- | :--- | :--- |
| V-21 | Catálogo global (28) | Tabla | Clubes + líderes + estado · "No hay clubes registrados" |
| V-22 | Detalle club GBP (30) | Panel | Info + líder actual · aviso si `Pending Leader` |
| V-23 | Buzón de trámites (31) | Tabla/bandeja | PDFs + estado del trámite · "No hay trámites por revisar" |
| V-24 | Configuración PAO (32) | Tabla | Períodos + fechas · "No hay períodos configurados" |
| V-25 | Histórico por PAO (33) | Tabla | Clubes + líderes del período · "No hay información histórica para este período" |

### Dos patrones reutilizables

1. **Dualidad de privacidad:** detalle público (V-02) vs. nómina interna (V-03); contador (V-01) vs. tabla (V-13). Es **un mismo componente con dos modos de render**, gobernado por RN-3. En Django se traduce en **dos serializers** sobre la misma entidad.
2. **Estados vacíos:** son parte intencional del diseño; muchas vistas arrancan vacías y deben tener un mensaje explícito, no una tabla en blanco.

---

## 14. Contrato de operaciones (superficie funcional)

Esta es la lista completa de operaciones que hoy expone `js/data-service.js` —el único punto de acceso a datos del frontend— y que el backend debe cubrir. **Es el contrato a reimplementar en Django.**

### Lectura de catálogos y perfiles

| Operación | Descripción | Regla |
| :--- | :--- | :--- |
| `getCatalogos()` | Facultades, áreas de interés, períodos PAO | — |
| `getProfileByEnrollment(enrollment)` / `getProfileById(id)` | Perfil del estudiante | — |
| `updateProfile(enrollment, patch)` | Edita descripción, habilidades y redes | F-07 |

### Clubes

| Operación | Descripción | Regla |
| :--- | :--- | :--- |
| `getClubs()` / `getClubById(id)` | Catálogo y detalle | RF-46 |
| `updateClub(clubId, patch)` | Edita datos del club | RF-14 |
| `addClubDocument(clubId, {title, file_url, is_public})` | Agrega documento | RNF-08 |
| `deleteClubDocument(docId)` | Elimina documento | — |
| `setDocVisibility(docId, isPublic)` | Cambia público/privado | RF-16 |

### Roles

| Operación | Descripción | Regla |
| :--- | :--- | :--- |
| `getClubRoles(clubId)` | Roles del club | RF-06 |
| `addRole(clubId, {role_name, is_leadership, permissions})` | Crea rol personalizado | RF-07 |
| `updateRole(roleId, patch)` / `deleteRole(roleId)` | Edita/elimina rol | RN-7 |
| `isRoleInUse(roleId)` | ¿hay membresías con ese rol? (bloquea el borrado) | — |

### Membresías

| Operación | Descripción | Regla |
| :--- | :--- | :--- |
| `isActiveMember(studentId, clubId)` | Verifica membresía activa | RN-3 |
| `getClubMembers(clubId, {onlyActive})` | Nómina con perfil y rol resueltos | RF-48 |
| `setMembershipRole(membershipId, roleId)` | Cambia el rol | RF-09 |
| `revokeMembership(membershipId)` | Baja lógica (`Revoked`) | RF-19 |
| `getNomina(clubId, paoPeriod)` | Membresías por período | RF-39 |
| `renewNomina(clubId, membershipIds)` | Crea membresías `Active` en el PAO vigente copiando `student_id` y `role_id` | RF-21 |

### Formularios

| Operación | Descripción | Regla |
| :--- | :--- | :--- |
| `getClubForms(clubId)` / `getFormById(id)` | Lectura | RF-22 |
| `getMembershipForm(clubId)` | Formulario de membresía activo más reciente | RF-25 |
| `formHasResponses(formId)` | ¿ya tiene solicitudes o inscripciones? | RF-24 |
| `saveForm({club_id, form_type, event_id, title, fields})` | Crea formulario con `version = max(mismo club+tipo) + 1` | RF-24 |
| `updateForm(formId, patch)` | Edita **solo si no tiene respuestas** | RF-24 |
| `deleteForm(formId)` / `deactivateForm(formId)` | Elimina o desactiva | — |

### Solicitudes de membresía

| Operación | Descripción | Regla |
| :--- | :--- | :--- |
| `canApply(studentId, clubId)` | Devuelve `{allowed, reason}`. Bloquea si es miembro activo o tiene `Pending` | **RN-2** |
| `addSolicitud({student_id, club_id, form_id, responses})` | Crea solicitud `Pending` | RF-25 |
| `getClubSolicitudes(clubId, status)` | Bandeja del líder | RF-26 |
| `approveSolicitud(sol)` | Marca `Approved` **y crea la `Membership` activa** con el rol Miembro y las fechas del PAO activo | RF-08, RF-27 |
| `rejectSolicitud(id, feedback)` | Marca `Rejected` con feedback | **RN-5** |

### Eventos, inscripciones y QR

| Operación | Descripción | Regla |
| :--- | :--- | :--- |
| `getVisibleEvents(studentId)` | **Devuelve todos los eventos**, incluidos `MembersOnly` (son visibles; el bloqueo es solo del registro) | RF-31 |
| `getEventById(id)` | Detalle | — |
| `getClubEvents(clubId)` | Eventos con métricas inscritos/asistentes | RF-38 |
| `addEvent(clubId, data)` / `updateEvent(id, patch)` | CRUD de evento | RF-30 |
| `eventHasRegistrations(eventId)` / `deleteEvent(id)` | Borrado condicionado | — |
| `getEventStaff(eventId)` / `setEventStaff(eventId, studentIds)` | Staff por evento | RF-35 |
| `canRegisterEvent(studentId, event)` | Cadena de validación: ya inscrito → sin formulario → `MembersOnly` y no miembro → fecha límite excedida | RF-31, RF-34 |
| `addInscripcion({event_id, student_id, form_id, responses})` | Crea inscripción, genera `qr_token`, `qr_status: Active`, `attendance_status: Registered` | RF-32 |
| `registerScan(qrToken, staffStudentId)` | Valida el token: vacío → desconocido → ya usado → registra asistencia y marca `Used` | **RN-6**, RF-36 |
| `getInscripcionesAll()` / `getAsistenciasAll()` | Lecturas | RF-38 |

### Notificaciones e historial

| Operación | Descripción | Regla |
| :--- | :--- | :--- |
| `getNotificacionesForUser(userId)` | Notificaciones del usuario, **ordenadas por fecha descendente** | RF-51 |
| `markNotificationsRead(ids)` | Marca como leídas | RF-51 |
| `getStudentHistory(studentId)` | Postulaciones + asistencias del estudiante | RF-50 |

### PAO

| Operación | Descripción | Regla |
| :--- | :--- | :--- |
| `getPaos()` / `getActivePao()` | Lectura | RF-45 |
| `addPao({pao_period, start_date, end_date, status})` | Crea período | RF-45 |
| `updatePao(paoPeriod, patch)` | Edita; **activar uno cierra los demás** | RF-45 |

### Trámites GBP

| Operación | Descripción | Regla |
| :--- | :--- | :--- |
| `getClubTramites(clubId)` | Trámites del club | RF-40 |
| `addTramite(clubId, {pao_period, document_type, file_url})` | Crea trámite en `Submitted` | RF-40, RF-41 |
| `setTramiteStatus(id, status, feedback, gbpId)` | GBP resuelve; rechazo exige feedback | RF-43, **RN-5** |

### GBP — catálogo y liderazgo

| Operación | Descripción | Regla |
| :--- | :--- | :--- |
| `getGlobalCatalog()` | Clubes con líder resuelto y conteo de miembros activos | RF-49 |
| `getClubLeader(club)` | Perfil del líder por matrícula | — |
| `addClub({...})` | Crea club; `Active` si la matrícula tiene cuenta, `Pending Leader` si no | RF-11, RF-12 |
| `revokeLeader(clubId)` | `leader_enrollment = null`, `status = Pending Leader` | RF-13 |
| `assignLeader(clubId, enrollment)` | Asigna/reasigna; activa si la matrícula existe | RF-13 |
| `getHistoryByPao(paoPeriod)` | Clubes, líderes y nómina del período | RF-49 |

### Utilidades de presentación (`js/utils.js`)

| Operación | Descripción |
| :--- | :--- |
| `label(v)` | Traduce un enum al español (§18) |
| `statusBadgeClass(status)` | Clase de badge según estado: éxito (`Approved`, `Active`, `Attended`, `Used`), peligro (`Rejected`, `Revoked`, `Expired`, `NoShow`), alerta (el resto) |
| `fmtDate(iso)` / `fmtDateTime(iso)` | Formato `es-EC` |
| `esc(s)` | Escapa HTML |

---

## 15. Arquitectura actual — Fase 1

### 15.1 Principios

- **Sin build:** HTML + Tailwind por CDN + JavaScript ES6 nativo con módulos.
- **Una sola fuente de datos** (`data/*.json`) y **un solo punto de acceso** (`js/data-service.js`). Esta es la decisión que abarata la migración: en Fase 2 **solo cambia ese archivo** para apuntar a la API, sin tocar las pantallas.
- **Escritura simulada:** un *overlay* en `localStorage` que se fusiona sobre los `.json` base al leer. Nada se persiste realmente.
- **Sesión mock:** `localStorage['espolclub_session']` con la forma `{ enrollment, email, role, club_id, role_id, student_id, name }`.

### 15.2 Estructura de carpetas

```
espolclub/
│
├── index.html                  → Punto de entrada: Inicio de sesión (1)
├── README.md                   → Documentación general
├── requirements.md             → Requerimientos
├── frontend_design.md          → Diseño de la Fase 1
├── pages_description.md        → Descripción archivo por archivo
├── MASTER.md                   → ESTE documento
│
├── assets/img/
│   ├── clubes/                 → Portadas de clubes (club_1..club_8)
│   └── events/                 → Imágenes de marketing
│
├── css/
│   └── themes.css              → Paleta y tema claro/oscuro (variables CSS)
│
├── data/                       → 12 .json simulados
│   ├── usuarios.json           → mock_credentials + profiles
│   ├── clubes.json
│   ├── roles.json
│   ├── membresias.json
│   ├── formularios.json
│   ├── solicitudes.json
│   ├── eventos.json
│   ├── inscripciones.json
│   ├── asistencias.json
│   ├── tramites_gbp.json
│   ├── notificaciones.json
│   └── catalogos.json
│
├── js/
│   ├── theme-init.js           → Aplica el tema antes del primer pintado (anti-FOUC)
│   ├── app.js                  → Header, navegación por entorno, tema, notificaciones, guarda de sesión
│   ├── data-service.js         → ÚNICO acceso a datos (fetch + overlay)
│   ├── auth.js                 → Login mock, sesión y enrutamiento por rol
│   ├── utils.js                → label(), fmtDate(), esc(), eventImage()
│   ├── components/
│   │   ├── card-club.js        → Tarjeta de club
│   │   └── dynamic-form.js     → Render y validación de formularios dinámicos
│   └── pages/
│       ├── auth/               → login, registro, verificacion, recuperacion
│       ├── movil/              → catalogo, club-detalle, eventos, credencial-qr,
│       │                          escaner-qr, perfil, solicitudes
│       ├── lider/              → panel, club, miembros, roles, solicitudes,
│       │                          formularios, eventos, nomina-pao, rendicion, bitacora
│       └── gbp/                → catalogo-global, alta-club, club-detalle,
│                                  tramites, pao, historico
│
└── pages/
    ├── auth/                   → registro.html, verificacion.html, recuperacion.html
    ├── movil/                  → catalogo, club-detalle, eventos, credencial-qr,
    │                              escaner-qr, perfil, solicitudes
    ├── lider/                  → panel, club, miembros, roles, solicitudes,
    │                              formularios, eventos, nomina-pao, rendicion, bitacora
    └── gbp/                    → catalogo-global, alta-club, club-detalle,
                                   tramites, pao, historico
```

### 15.3 Convenciones de las páginas HTML

- En el `<head>`: `theme-init.js` (tema antes de pintar) → Tailwind CSS por CDN → `css/themes.css`.
- El `<body>` declara su contexto con atributos `data-*`:
  - `data-root` — ruta relativa a la raíz (ej. `../../`)
  - `data-env` — `movil` \| `lider` \| `gbp`
  - `data-active` — ítem de menú activo
  - `data-protected` — exige sesión
  - `data-roles` — roles permitidos (ej. `Líder de Club`)
- `<header id="app-header">` lo llena `app.js`.
- Al final del `<body>` se cargan `app.js` (chrome común) y el `.js` específico de la pantalla, ambos como `type="module"`.

### 15.4 Agrupación de pantallas en archivos

Algunos archivos HTML implementan varias pantallas del inventario mediante modales:

| Archivo | Pantallas |
| :--- | :--- |
| `pages/movil/club-detalle.html` | 7 (detalle) + 8 (postulación, en modal) |
| `pages/movil/eventos.html` | 9 (grilla) + 10 (detalle, modal) + 11 (inscripción, modal) |
| `pages/movil/perfil.html` | 14 (perfil) + 15 (historial) |
| `pages/lider/eventos.html` | 23 (tabla) + 24 (crear/editar, modal) + 25 (staff, modal) |
| Cabecera (`app.js`) | 5 (centro de notificaciones) |

---

## 16. Arquitectura objetivo — Django

Esta sección es el **blueprint de construcción** de la Fase 2/3.

### 16.1 Decisión de stack

> **Cambio respecto de la documentación original.** El `README.md` y `requirements.md` definen la Fase 2 sobre **FastAPI**. Este documento se emite para construir el backend con **Django**. Nada del análisis, las reglas de negocio ni el modelo de datos cambia por ello: son independientes del framework. Lo que cambia es la implementación (ORM de Django en vez de SQLAlchemy, DRF en vez de Pydantic + routers de FastAPI, y el panel `django-admin` como bono para GBP).

**Stack propuesto:**

| Componente | Elección | Motivo |
| :--- | :--- | :--- |
| Framework | Django 5.x | ORM, migraciones, admin y auth incluidos |
| API | Django REST Framework | Serializers diferenciados por contexto (RNF-06) |
| Base de datos | PostgreSQL | `JSONField` nativo para `permissions`, `fields` y `responses` |
| Autenticación | `djangorestframework-simplejwt` | RNF-04 exige JWT |
| Tareas programadas | Celery + Celery Beat, o un `management command` invocado por cron | RF-20 (congelar PAO) y RF-37 (expirar QR) |
| Exportaciones | `openpyxl` (`.xlsx`), `reportlab` o `WeasyPrint` (`.pdf`) | RF-42 |
| Firma de tokens QR | `django.core.signing` (`TimestampSigner` / `dumps`) | RNF-05 |
| CORS | `django-cors-headers` | El frontend estático y React Native consumen la API |

### 16.2 Estructura de apps propuesta

Un app por dominio del negocio, espejando las máquinas de estado de §5:

```
espolclub_backend/
├── manage.py
├── config/                     # settings, urls, wsgi/asgi
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── celery.py
├── apps/
│   ├── accounts/               # Student (AUTH_USER_MODEL), registro, verificación, JWT
│   ├── clubs/                  # Club, ClubDocument, Role, Membership
│   ├── forms/                  # Form (esquema dinámico) + validación de respuestas
│   ├── applications/           # MembershipApplication (RN-2, RN-5)
│   ├── events/                 # Event, EventRegistration, EventAttendance, EventStaff, QR
│   ├── gbp/                    # PaoPeriod, GbpDocumentProcess, exportaciones
│   └── notifications/          # Notification + emisores de eventos de dominio
└── fixtures/                   # datos semilla equivalentes a data/*.json
```

**Criterio de frontera:** `accounts` no conoce a nadie; `clubs` conoce `accounts`; `forms` conoce `clubs`; `applications` y `events` conocen `forms` y `clubs`; `gbp` conoce `clubs`; `notifications` es consumidor de señales y no lo conoce nadie.

### 16.3 Traducción del modelo a Django

**Reglas generales de traducción:**

1. `Student` debe ser el `AUTH_USER_MODEL` (heredando de `AbstractBaseUser` + `PermissionsMixin`), con `enrollment` como `USERNAME_FIELD`. El login del sistema es por matrícula o correo.
2. Los campos JSON (`permissions`, `fields`, `responses`, `skills`, `social_media`) van como `models.JSONField`.
3. `Club.members_count` y `Event.stats` **no se almacenan**: se exponen como propiedades calculadas o anotaciones (`annotate(Count(...))`) en el serializer. En la Fase 1 estaban denormalizados porque no había servidor.
4. `Club.internal_documents` se promueve a la tabla `ClubDocument`.
5. `EventStaff` se crea como tabla real (hoy solo vive en `localStorage`).
6. Todos los enums se declaran con `models.TextChoices`, **con valores en inglés y etiquetas en español** — resuelve RNF-10 de forma nativa vía `get_FOO_display()`.
7. Nada se borra físicamente: usar cambios de estado. Donde se necesite borrado (roles sin uso, formularios sin respuestas, eventos sin inscripciones), condicionarlo con la comprobación previa correspondiente.

**Esqueleto de `models.py` (referencia):**

```python
# apps/accounts/models.py
class Student(AbstractBaseUser, PermissionsMixin):
    enrollment   = models.CharField(max_length=20, unique=True)   # clave natural
    first_name   = models.CharField(max_length=80)
    last_name    = models.CharField(max_length=80)
    birth_date   = models.DateField(null=True, blank=True)
    email        = models.EmailField(unique=True)                 # validar @espol.edu.ec
    semester     = models.PositiveSmallIntegerField(null=True, blank=True)
    faculty      = models.CharField(max_length=20, blank=True)
    career       = models.CharField(max_length=120, blank=True)
    description  = models.TextField(blank=True)
    skills       = models.JSONField(default=list, blank=True)
    social_media = models.JSONField(default=list, blank=True)     # [{network, link}]
    is_gbp_admin = models.BooleanField(default=False)             # perfil institucional
    is_verified  = models.BooleanField(default=False)             # RF-01
    USERNAME_FIELD = 'enrollment'

    @property
    def age(self):  # la edad se deriva, no se almacena
        ...

# apps/clubs/models.py
class Club(models.Model):
    class Status(models.TextChoices):
        ACTIVE  = 'Active', 'Activo'
        PENDING = 'Pending Leader', 'Sin líder'

    name           = models.CharField(max_length=150)
    acronym        = models.CharField(max_length=30)
    description    = models.TextField()
    location       = models.CharField(max_length=120)
    faculty        = models.CharField(max_length=20, blank=True)
    interest_areas = models.JSONField(default=list)      # >= 1, catálogo cerrado
    image          = models.CharField(max_length=255, blank=True)
    leader         = models.ForeignKey(Student, null=True, blank=True,
                                       on_delete=models.SET_NULL, related_name='led_club')
    status         = models.CharField(max_length=20, choices=Status.choices)
    social_media   = models.JSONField(default=list, blank=True)

    @property
    def members_count(self):
        return self.memberships.filter(status=Membership.Status.ACTIVE).count()

class ClubDocument(models.Model):
    club      = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='documents')
    title     = models.CharField(max_length=150)
    file      = models.FileField(upload_to='clubs/docs/')   # validar .pdf
    is_public = models.BooleanField(default=False)          # RF-16

class Role(models.Model):
    club          = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='roles')
    role_name     = models.CharField(max_length=80)
    is_default    = models.BooleanField(default=False)
    is_leadership = models.BooleanField(default=False)
    permissions   = models.JSONField(default=dict)   # clave ausente = False

    class Meta:
        constraints = [models.UniqueConstraint(fields=['club', 'role_name'],
                                               name='uniq_role_per_club')]

    def has(self, perm):
        return bool(self.permissions.get(perm, False))

class Membership(models.Model):
    class Status(models.TextChoices):
        ACTIVE  = 'Active',  'Activa'
        FROZEN  = 'Frozen',  'Congelada'
        EXPIRED = 'Expired', 'Expirada'
        REVOKED = 'Revoked', 'Revocada'

    student     = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='memberships')
    club        = models.ForeignKey(Club,    on_delete=models.CASCADE, related_name='memberships')
    role        = models.ForeignKey(Role,    on_delete=models.PROTECT)
    pao_period  = models.ForeignKey('gbp.PaoPeriod', on_delete=models.PROTECT)
    valid_from  = models.DateField()
    valid_until = models.DateField()
    status      = models.CharField(max_length=10, choices=Status.choices)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['student', 'club', 'pao_period'],
                                               name='uniq_membership_per_pao')]

    def clean(self):
        # RF-09: el rol debe pertenecer al mismo club
        # RN-1: si role.is_leadership y status=Active, el estudiante no puede
        #       tener otra membresía activa de liderazgo en otro club
        ...
```

Los modelos de `forms`, `applications`, `events`, `gbp` y `notifications` siguen literalmente las tablas de §7.2 con las restricciones de §7.4. Puntos que **no** se pueden omitir:

```python
# apps/events/models.py
class EventAttendance(models.Model):
    class Meta:
        constraints = [models.UniqueConstraint(fields=['event', 'student'],
                                               name='uniq_attendance')]   # RN-6

class EventRegistration(models.Model):
    qr_token = models.CharField(max_length=255, unique=True)              # RNF-05
    class Meta:
        constraints = [models.UniqueConstraint(fields=['event', 'student'],
                                               name='uniq_registration')]

# apps/gbp/models.py
class PaoPeriod(models.Model):
    pao_period = models.CharField(max_length=10, primary_key=True)
    # solo uno Active: UniqueConstraint condicional
    class Meta:
        constraints = [models.UniqueConstraint(fields=['status'],
                                               condition=Q(status='Active'),
                                               name='single_active_pao')]
```

### 16.4 Autenticación y cuentas

| Requisito | Implementación |
| :--- | :--- |
| Registro solo `@espol.edu.ec` (RF-01) | `EmailValidator` + validador propio de dominio en el serializer de registro |
| Verificación por enlace (RF-01) | Token firmado con `django.core.signing.dumps({'pk': id})` enviado por correo; endpoint `GET /auth/verify/<token>/` marca `is_verified = True` |
| Matrícula única (RF-05) | `unique=True` en `enrollment` + mensaje explícito en el serializer |
| Login (RF-02) | `POST /auth/login/` → par de tokens JWT. Acepta `enrollment` **o** `email` como identificador |
| Recuperación (RF-03) | Flujo estándar de Django (`PasswordResetView`) adaptado a API |
| Activación diferida de líder (RF-12) | Señal `post_save` en `Student`: si existe un `Club` con `leader_enrollment` igual a la matrícula recién registrada, vincularlo, ponerlo `Active` y crear la `Membership` con el rol Presidente/a |
| Roles de aplicación | Derivar, no almacenar: `is_gbp_admin` → *Administrador GBP*; membresía activa con rol `is_leadership` → *Líder de Club*; cualquier membresía activa → *Miembro del Club*; el resto → *Estudiante Politécnico* |

### 16.5 Sistema de permisos

**No usar el sistema de permisos de Django para los permisos de club.** Los permisos son **por club y por rol**, con un diccionario extensible; el modelo de `auth.Permission` es global. Implementar clases de permiso propias de DRF:

```python
class HasClubPermission(BasePermission):
    """Exige que el usuario tenga una Membership Active en el club del objeto
    cuyo Role.permissions contenga la clave requerida en True."""
    required_perm = None   # ej. 'manage_members'

class IsGbpAdmin(BasePermission):
    """request.user.is_gbp_admin"""

class IsClubMember(BasePermission):
    """Membership Active en el club — habilita la vista de nómina interna (RN-3)."""

class IsEventStaff(BasePermission):
    """Asignado como EventStaff del evento Y el evento está en curso (RF-35)."""

class IsSelf(BasePermission):
    """Solo el propio estudiante edita su perfil (F-07)."""
```

**Restricción especial (RN-7):** `manage_roles` solo puede otorgarse a roles con `is_leadership = true`, y por defecto solo lo tiene Presidente/a. Validar en el serializer de `Role`.

### 16.6 Endpoints REST propuestos

Traducción directa del contrato de §14. Prefijo `/api/v1/`.

**Auth**
```
POST   /auth/register/                     Registro (RF-01)
GET    /auth/verify/<token>/               Verificación de correo
POST   /auth/login/                        JWT (RF-02)
POST   /auth/refresh/                      Refresh token
POST   /auth/password-reset/               Solicitud (RF-03)
POST   /auth/password-reset/confirm/       Confirmación
GET    /auth/me/                           Sesión actual (rol derivado, club_id, role_id)
```

**Catálogos**
```
GET    /catalogs/                          Facultades, áreas de interés, PAOs
```

**Estudiantes**
```
GET    /students/me/                       Perfil propio (RF-50)
PATCH  /students/me/                       Editar descripción, skills, redes (F-07)
GET    /students/me/history/               Postulaciones + asistencias (RF-50)
GET    /students/me/registrations/         Credenciales QR (pantalla 12)
```

**Clubes**
```
GET    /clubs/                             Catálogo filtrable ?q=&faculty=&area= (RF-46)
POST   /clubs/                             Alta — solo GBP (RF-11/12)
GET    /clubs/{id}/                        Detalle; serializer según privacidad (RN-3)
PATCH  /clubs/{id}/                        Editar — manage_club_info (RF-14)
GET    /clubs/{id}/members/                Nómina — miembros y GBP (RF-48)
POST   /clubs/{id}/leader/revoke/          Revocar líder — GBP (RF-13)
POST   /clubs/{id}/leader/assign/          Asignar líder — GBP (RF-13)
GET    /clubs/{id}/documents/              Documentos (filtra privados si no es miembro)
POST   /clubs/{id}/documents/              Subir PDF — manage_documents
PATCH  /clubs/documents/{doc_id}/          Cambiar visibilidad (RF-16)
DELETE /clubs/documents/{doc_id}/
```

**Roles y membresías**
```
GET    /clubs/{id}/roles/                  Roles del club (RF-06)
POST   /clubs/{id}/roles/                  Crear rol — manage_roles (RF-07, RN-7)
PATCH  /roles/{id}/                        Editar rol
DELETE /roles/{id}/                        Solo si no está en uso
PATCH  /memberships/{id}/                  Cambiar role_id — manage_members (RF-09)
POST   /memberships/{id}/revoke/           Baja lógica (RF-19)
GET    /clubs/{id}/nomina/?pao=2026-I      Nómina por período (RF-39)
POST   /clubs/{id}/nomina/renew/           Renovar al PAO activo (RF-21)
```

**Formularios**
```
GET    /clubs/{id}/forms/                  Formularios del club (RF-22)
POST   /clubs/{id}/forms/                  Crear (calcula version) — manage_forms
GET    /forms/{id}/                        Esquema para renderizar (RF-23)
PATCH  /forms/{id}/                        409 si ya tiene respuestas (RF-24)
GET    /clubs/{id}/forms/membership/       Formulario de membresía activo (RF-25)
```

**Solicitudes**
```
GET    /clubs/{id}/applications/?status=Pending    Bandeja del líder (RF-26)
POST   /clubs/{id}/applications/                   Postular — valida RN-2 (RF-25)
GET    /clubs/{id}/applications/can-apply/         {allowed, reason} (RN-2)
POST   /applications/{id}/approve/                 Crea Membership (RF-08, RF-27)
POST   /applications/{id}/reject/                  Exige feedback (RN-5)
```

**Eventos, QR y asistencia**
```
GET    /events/                            Eventos visibles (incluye MembersOnly) (RF-31)
GET    /events/{id}/                       Detalle + {can_register, reason} (RF-34)
GET    /clubs/{id}/events/                 Con métricas inscritos/asistentes (RF-38)
POST   /clubs/{id}/events/                 Crear — manage_events (RF-30)
PATCH  /events/{id}/                       Editar
DELETE /events/{id}/                       Solo si no tiene inscripciones
GET    /events/{id}/staff/                 Staff asignado (RF-35)
PUT    /events/{id}/staff/                 Reemplaza la asignación
POST   /events/{id}/register/              Inscribirse; emite qr_token (RF-32)
GET    /events/{id}/registrations/         Bitácora de inscritos (pantalla 34)
POST   /attendance/scan/                   {qr_token} → valida y registra (RN-6, RF-36)
```

**GBP**
```
GET    /gbp/clubs/                         Catálogo global con líderes (RF-49)
GET    /gbp/processes/                     Buzón de trámites (RF-42)
POST   /clubs/{id}/processes/              Enviar reporte — submit_gbp_reports (RF-40)
POST   /gbp/processes/{id}/review/         Aprobar/rechazar (RF-43, RN-5)
GET    /gbp/processes/export/?format=xlsx  Exportación consolidada (RF-42)
GET    /gbp/pao/                           Períodos (RF-45)
POST   /gbp/pao/                           Crear período
PATCH  /gbp/pao/{pao_period}/              Editar; activar cierra los demás
GET    /gbp/history/?pao=2025-II           Histórico por período (RF-49)
```

**Notificaciones**
```
GET    /notifications/                     Del usuario, orden desc (RF-51)
POST   /notifications/read/                Marca ids como leídas
```

### 16.7 Serializers diferenciados (RNF-06 / RN-3)

La privacidad por contexto se implementa con **dos serializers sobre la misma entidad**, elegidos en `get_serializer_class()` según quién consulta:

| Entidad | Serializer público (móvil, no miembro) | Serializer interno (miembro / GBP) |
| :--- | :--- | :--- |
| `Club` | `ClubPublicSerializer`: datos generales + **solo `members_count`** + documentos con `is_public=True` | `ClubInternalSerializer`: agrega la nómina detallada y todos los documentos |
| `Membership` | *(no se expone)* | `MembershipSerializer`: nombre, matrícula, carrera, correo, rol, vigencia |
| `Student` | `StudentCardSerializer`: nombre público mínimo | `StudentFullSerializer`: matrícula, correo, facultad, carrera, semestre |

**Prueba de aceptación:** un `GET /clubs/2/` hecho por un estudiante que no es miembro **nunca** debe contener nombres ni correos de miembros en el cuerpo de la respuesta.

### 16.8 Procesos automáticos

| Proceso | Disparador | Acción | Regla |
| :--- | :--- | :--- | :--- |
| **Congelamiento por PAO** | Diario | Membresías `Active` cuyo `valid_until < hoy` → `Frozen` | RF-20, RN-4 |
| **Expiración de membresías** | Diario | Membresías `Frozen` de PAOs cerrados sin renovación → `Expired` | RF-19 |
| **Expiración de QR** | Cada hora | `EventRegistration.qr_status = Active` cuyo evento superó `end_datetime` → `Expired` | RF-37 |
| **Marcado de NoShow** | Tras `end_datetime` | Inscripciones con `attendance_status = Registered` de eventos finalizados → `NoShow` | §5.4 |
| **Emisión de notificaciones** | Señales de dominio | Al cambiar estado de solicitud, membresía o trámite, crear `Notification` | RF-51 |

Implementar como `management commands` idempotentes (`python manage.py freeze_expired_memberships`) y programarlos con Celery Beat o cron. Deben poder ejecutarse dos veces sin efectos duplicados.

### 16.9 Generación y validación del token QR

```python
from django.core import signing

def issue_qr_token(registration):
    # Opaco: el payload solo referencia la inscripción, y va firmado.
    return signing.dumps({'r': registration.id}, salt='espolclub.qr')

def validate_scan(qr_token, staff_student, now):
    reg = EventRegistration.objects.select_for_update().filter(qr_token=qr_token).first()
    if not reg:                                   return 'invalid'   # Credencial no reconocida
    if reg.qr_status == 'Used' or reg.attendance_status == 'Attended':
        return 'duplicate'                                           # Ya registró asistencia
    if reg.qr_status == 'Expired':                return 'expired'
    if not EventStaff.objects.filter(event=reg.event, student=staff_student).exists():
        return 'unauthorized'                                        # RF-35
    # transacción: crea la asistencia y marca el token
    ...
```

**Puntos no negociables:**
- El token **no** debe contener `student_id` ni `event_id` legibles.
- La validación se hace **contra la base de datos**, no descifrando el token.
- El escaneo corre dentro de una transacción con bloqueo; la restricción `UNIQUE(event_id, student_id)` es la última línea de defensa contra el reescaneo concurrente.
- `scanned_at` lo pone el **servidor**, nunca el cliente (RNF-12).
- El escaneo solo es válido si quien escanea está en `EventStaff` de **ese** evento.

### 16.10 Exportaciones (RF-42)

| Formato | Uso | Librería |
| :--- | :--- | :--- |
| `.xlsx` | Datos tabulares: nóminas, listas de asistencia, catálogo consolidado | `openpyxl` |
| `.pdf` | Documentos de texto: reportes, constancias | `reportlab` o `WeasyPrint` |

**No dar soporte a `.doc`/`.docx`** (RNF-08). Validar la extensión y el content-type en la subida de archivos, no solo el nombre.

### 16.11 Plan de migración desde la Fase 1

| Etapa | Trabajo | Verificación |
| :--- | :--- | :--- |
| 1 | Modelos + migraciones + `django-admin` registrado | Se pueden crear todas las entidades desde el admin |
| 2 | Fixtures cargados desde §17 | `loaddata` reproduce exactamente el estado de la Fase 1 |
| 3 | Auth con JWT y roles derivados | Los 4 usuarios semilla inician sesión y `/auth/me/` devuelve el rol correcto |
| 4 | Endpoints de lectura (`GET`) con serializers diferenciados | Un no-miembro no ve la nómina de un club |
| 5 | Endpoints de escritura con reglas RN-1..RN-7 | Cada regla tiene una prueba que verifica que el rechazo ocurre |
| 6 | Procesos automáticos (§16.8) | Ejecutados dos veces no duplican efectos |
| 7 | **Reescribir `js/data-service.js`** para llamar a la API | Ninguna pantalla del frontend cambia |
| 8 | Exportaciones y notificaciones | GBP descarga `.xlsx`; los cambios de estado generan notificación |

> **La etapa 7 es el punto de convergencia del diseño:** todo el frontend de la Fase 1 pasa a datos reales cambiando **un solo archivo**, porque ninguna pantalla accede a los datos directamente.

---

## 17. Datos semilla / fixtures

Reproducen exactamente el estado de la Fase 1. La **coherencia entre ellos es deliberada** y sirve para probar cada regla de negocio.

### 17.1 Usuarios y credenciales

> ⚠️ Las contraseñas en texto plano son **intencionales y exclusivas del prototipo**. En Django deben cargarse con `set_password()`.

| Rol simulado | `enrollment` | Contraseña | `student_id` | Entorno |
| :--- | :--- | :--- | :--- | :--- |
| Estudiante Politécnico | `202311346` | `estudiante123` | 1 | Móvil |
| Miembro del Club | `202055789` | `miembro123` | 2 | Móvil |
| Líder de Club | `201899001` | `lider123` | 3 | Web / Móvil |
| Administrador GBP | `GBP-001` | `gbp123` | 4 | Web |

**Perfiles completos (6):**

| id | enrollment | Nombre | Facultad | Carrera | Semestre | Notas |
| :-- | :--- | :--- | :--- | :--- | :-- | :--- |
| 1 | 202311346 | Kevin Maldonado | FIEC | Computación | 6 | **No** es miembro de KOKOA; tiene una postulación `Rejected` |
| 2 | 202055789 | María Cevallos | FIEC | Telemática | 7 | Miembro activo; tiene membresía `Frozen` de 2025-II |
| 3 | 201899001 | Diego Ponce | FIEC | Computación | 9 | Líder (Presidente/a) de KOKOA |
| 4 | GBP-001 | Ana Rivas | — | — | — | Administradora GBP |
| 5 | 202144556 | Lucía Torres | FCNM | Matemática | 4 | Autora de la solicitud `Pending` |
| 6 | 201977882 | Andrés Vera | FIEC | Computación | 8 | Rol personalizado; escaneó la asistencia registrada |

### 17.2 Clubes

| id | Nombre | Acrónimo | Facultad | Áreas | Líder | Estado |
| :-- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2 | Club de Software Libre KOKOA | KOKOA | FIEC | Tecnología, Académico | `201899001` | `Active` |
| 4 | Club de Mecatrónica | MECATRÓNICA | FIMCP | Tecnología, Ciencia | `202099777` *(sin cuenta)* | `Pending Leader` |

**Documentos de KOKOA:** `101` Estatutos del Club (privado), `102` Brochure 2026 (público) — cubren ambos lados de RF-16.

### 17.3 Roles (club 2)

| id | Nombre | `is_default` | `is_leadership` |
| :-- | :--- | :-- | :-- |
| 7 | Presidente/a | ✔ | ✔ (todos los permisos) |
| 8 | Vicepresidente/a | ✔ | ✔ |
| 9 | Secretario/a | ✔ | ✔ |
| 10 | Miembro | ✔ | ✘ (sin permisos) |
| 11 | Encargado de Documentos | ✘ | ✘ (rol personalizado) |

### 17.4 Membresías

| id | Estudiante | Club | Rol | PAO | Estado |
| :-- | :-- | :-- | :-- | :--- | :--- |
| 2001 | 3 (Diego) | 2 | 7 Presidente/a | 2026-I | `Active` |
| 2002 | 2 (María) | 2 | 10 Miembro | 2026-I | `Active` |
| 2003 | 6 (Andrés) | 2 | 11 Encargado de Documentos | 2026-I | `Active` |
| 1999 | 2 (María) | 2 | 10 Miembro | 2025-II | `Frozen` |

### 17.5 Períodos PAO

| `pao_period` | Inicio | Fin | Estado |
| :--- | :--- | :--- | :--- |
| 2025-II | 2025-10-13 | 2026-02-27 | `Closed` |
| 2026-I | 2026-05-01 | 2026-09-15 | `Active` |

### 17.6 Formularios

| id | Club | Tipo | Evento | Título | Campos |
| :-- | :-- | :--- | :-- | :--- | :--- |
| 301 | 2 | `Membership` | — | Formulario de Inscripción - KOKOA | `q1` textarea obligatorio (max 500), `q2` select obligatorio (3 opciones) |
| 302 | 2 | `Event` | 50 | Registro - Taller de Git | `f1` radio obligatorio (Principiante/Intermedio/Avanzado) |

### 17.7 Solicitudes

| id | Estudiante | Club | Estado | Feedback |
| :-- | :-- | :-- | :--- | :--- |
| 501 | 5 (Lucía) | 2 | `Pending` | — |
| 502 | 1 (Kevin) | 2 | `Rejected` | "Cupo lleno este PAO; vuelve a postular el próximo período." |

> Kevin no es miembro y su solicitud fue rechazada: eso permite probar la **reaplicación inmediata** (RF-29) sin chocar con la regla anti-duplicado (RN-2).

### 17.8 Eventos

| id | Nombre | Modalidad | Visibilidad | Formulario | Inscritos/Asistentes |
| :-- | :--- | :--- | :--- | :-- | :--- |
| 50 | CLI - Comandos Básicos Parte #1 | `Online` | `Public` | 302 | 2 / 1 |
| 51 | Reunión interna de directiva | `In-person` | `MembersOnly` | *(ninguno)* | 0 / 0 |

### 17.9 Inscripciones y asistencias

| Inscripción | Evento | Estudiante | `qr_status` | `attendance_status` |
| :-- | :-- | :-- | :--- | :--- |
| 7001 | 50 | 1 (Kevin) | `Active` | `Registered` |
| 7002 | 50 | 2 (María) | `Used` | `Attended` |

**Asistencia 8001:** inscripción 7002, evento 50, estudiante 2, escaneada por el staff 6 (Andrés). Cubre RN-6: intentar reescanear el token de 7002 debe fallar.

### 17.10 Trámites GBP

| id | Club | PAO | Tipo | Estado |
| :-- | :-- | :--- | :--- | :--- |
| 901 | 2 | 2026-I | Nómina de Miembros | `Under Review` |
| 902 | 2 | 2025-II | Nómina de Miembros | `Approved` |

### 17.11 Notificaciones

| id | Usuario | Tipo | Leída |
| :-- | :-- | :--- | :-- |
| 9001 | 1 | `application_rejected` | ✔ |
| 9002 | 1 | `event_registered` | ✘ |
| 9003 | 3 | `application_pending` | ✘ |
| 9004 | 3 | `gbp_review` | ✘ |

### 17.12 Cobertura de prueba de los datos semilla

| Dato | Permite probar |
| :--- | :--- |
| Club `Pending Leader` (id 4) | RF-12, panel en solo lectura, aviso de club sin líder |
| Membresía `Frozen` (id 1999) | RN-4, renovación de nómina (RF-21) |
| Solicitud `Rejected` de Kevin | RN-5, RF-29 (reaplicación inmediata) |
| Solicitud `Pending` de Lucía | RF-26, RF-27, bandeja del líder |
| Evento `MembersOnly` (id 51) | RF-31 (visible pero bloqueado) |
| Inscripción `Used`/`Attended` (7002) | RN-6 (no reescaneo) |
| Inscripción `Active`/`Registered` (7001) | Credencial QR válida, escaneo exitoso |
| Documentos 101/102 | RF-16 (visibilidad diferenciada) |
| Rol personalizado 11 | RF-07 |
| Dos PAOs (uno cerrado) | RF-45, RF-49 (histórico) |

---

## 18. Traducción de enumeraciones

Mapa canónico inglés → español (RNF-10). En Django se implementa con las etiquetas de `TextChoices`.

| Valor en BD | Etiqueta en UI | Entidad |
| :--- | :--- | :--- |
| `Pending` | Pendiente | Solicitud |
| `Approved` | Aprobada | Solicitud / Trámite |
| `Rejected` | Rechazada | Solicitud / Trámite |
| `Active` | Activa | Membresía / PAO / QR / Club |
| `Frozen` | Congelada | Membresía |
| `Expired` | Expirada | Membresía / QR |
| `Revoked` | Revocada | Membresía |
| `Submitted` | Enviado | Trámite GBP |
| `Under Review` | En revisión | Trámite GBP |
| `Registered` | Inscrito | Inscripción |
| `Attended` | Asistió | Inscripción / Asistencia |
| `NoShow` | No asistió | Inscripción |
| `Used` | Usado | QR |
| `Public` | Público | Evento |
| `MembersOnly` | Solo miembros | Evento |
| `In-person` | Presencial | Evento |
| `Virtual` | Virtual | Evento |
| `Pending Leader` | Sin líder | Club |
| `Closed` | Cerrado | PAO |

**Clases de badge por estado:**

| Clase | Estados |
| :--- | :--- |
| Éxito | `Approved`, `Active`, `Attended`, `Used` |
| Peligro | `Rejected`, `Revoked`, `Expired`, `NoShow` |
| Alerta (por defecto) | `Pending`, `Frozen`, `Submitted`, `Under Review`, `Registered` |

**Formato de fechas:** locale `es-EC`. Fecha: `19 jun 2026`. Fecha y hora: `19 jun 2026, 14:30`.

---

## 19. Matriz de trazabilidad

### 19.1 Clasificación de requerimientos por fase

Muchos requerimientos son **transversales**: se prototipan con mocks en F1, se implementan en F2, se exponen en F3 y se reconstruyen nativamente en F4.

**Exclusivos de cada fase:**

| Fase | Requerimientos exclusivos |
| :--- | :--- |
| **F1 — Frontend** | RF-04, RNF-02, RNF-07 |
| **F2 — Backend y BD** | RF-05, RF-06, RF-08, RF-09, RF-12, RF-13, RF-17, RF-18, RF-19, RF-20, RF-24, RF-28, RF-29, RF-33, RF-37, RF-39, RF-41, RF-44, RF-52, RNF-05, RNF-09, RNF-12 |
| **F3 — APIs** | *(ninguno propio; expone la lógica de F2 hacia F1 y F4)* |
| **F4 — App móvil** | RNF-11 |

**Transversales (resumen):**

| Requerimiento | Fases | Motivo |
| :--- | :--- | :--- |
| RF-01, RF-02, RF-03 | F1+F2+F3+F4 | UI simulada (F1), lógica real (F2), servicio (F3), login nativo (F4) |
| RF-07, RF-10, RF-11, RF-14, RF-15 | F1+F2 | Acción en web + lógica/persistencia en backend |
| RF-16 | F1+F2+F3+F4 | Toggle operado, persistido, respetado por API y mostrado en móvil |
| RF-21, RF-45 | F1+F2 | Iniciado en web + procesado en backend |
| RF-22 | F1+F2 | Constructor en web + persistencia del esquema |
| RF-23 | F2+F3+F4 (+F1 simulador) | Móvil renderiza/envía consumiendo API |
| RF-25, RF-32, RF-50 | F1+F2+F3+F4 | Acción del estudiante en todo el recorrido |
| RF-26, RF-30, RF-38, RF-40, RF-42, RF-43 | F1+F2 | Mostrado/operado en web + lógica en backend |
| RF-27 | F1+F2+F4 | Aprobar/rechazar en web y conveniencia móvil |
| RF-31, RF-46, RF-47, RF-48, RF-51 | F1+F2+F3+F4 | Regla/contrato en backend y API, reflejado en ambos frontends |
| RF-34, RF-35 | F1+F2+F4 | Regla en backend mostrada/operada en web y móvil |
| RF-36, RF-56, RF-57 | F2+F3+F4 | Escaneo/acción móvil validada por API |
| RF-49 | F1+F2+F3 | Histórico almacenado, consultado por API y mostrado |
| RF-53, RF-54 | F1+F2 | Acción en frontend web + autorización de backend |
| RF-55 | F1+F4 | Prototipo en simulador móvil + construcción nativa |
| RNF-01 | F1+F4 | Los dos entornos se materializan en sus frontends |
| RNF-04 | F2+F3 | JWT implementado en backend y protege rutas |
| RNF-06 | F1+F2+F3+F4 | Privacidad diferenciada como regla, contrato y presentación |
| RNF-08 | F1+F2 | Restricción en carga/visualización web y generación backend |
| RNF-10 | F1+F2+F4 | Enums en datos y traducción en presentación |
| RNF-03, RNF-13 | F1+F2+F3+F4 | Gobiernan todo el proyecto (proceso y licencia) |

**Cobertura:** 57 RF + 13 RNF. Dato clave de planificación: **la Fase 3 no tiene requerimientos propios**; el peso de la lógica vive en el backend.

### 19.2 Requerimiento → pantalla → entidad → endpoint

| RF | Pantalla(s) | Entidad principal | Endpoint objetivo |
| :--- | :--- | :--- | :--- |
| RF-01, RF-05 | 2, 3 | `Student` | `POST /auth/register/`, `GET /auth/verify/` |
| RF-02, RF-04 | 1 | `Student` | `POST /auth/login/` |
| RF-03 | 4 | `Student` | `POST /auth/password-reset/` |
| RF-06, RF-07, RF-10 | 20 | `Role` | `GET/POST /clubs/{id}/roles/` |
| RF-08, RF-27 | 21, 16 | `MembershipApplication`, `Membership` | `POST /applications/{id}/approve/` |
| RF-09, RF-19 | 19 | `Membership` | `PATCH /memberships/{id}/` |
| RF-11, RF-12, RF-14, RF-15 | 29 | `Club` | `POST /clubs/` |
| RF-13 | 30 | `Club`, `Membership` | `POST /clubs/{id}/leader/revoke|assign/` |
| RF-16 | 18 | `ClubDocument` | `PATCH /clubs/documents/{id}/` |
| RF-17, RF-18 | 19, 26 | `Membership` | `GET /clubs/{id}/members/` |
| RF-20, RF-21 | 26 | `Membership` | `POST /clubs/{id}/nomina/renew/` + tarea programada |
| RF-22, RF-24 | 22 | `Form` | `POST /clubs/{id}/forms/` |
| RF-23 | 8, 11 | `Form` | `GET /forms/{id}/` |
| RF-25, RF-28, RF-29 | 8 | `MembershipApplication` | `POST /clubs/{id}/applications/` |
| RF-26 | 21, 16 | `MembershipApplication` | `GET /clubs/{id}/applications/` |
| RF-30, RF-33 | 24 | `Event` | `POST /clubs/{id}/events/` |
| RF-31, RF-34 | 9, 10 | `Event` | `GET /events/{id}/` |
| RF-32 | 11, 12 | `EventRegistration` | `POST /events/{id}/register/` |
| RF-35 | 25 | `EventStaff` | `PUT /events/{id}/staff/` |
| RF-36, RF-37 | 13 | `EventAttendance` | `POST /attendance/scan/` |
| RF-38 | 23 | `Event` (derivado) | `GET /clubs/{id}/events/` |
| RF-39, RF-40, RF-41 | 27 | `GbpDocumentProcess` | `POST /clubs/{id}/processes/` |
| RF-42, RF-43, RF-44 | 31 | `GbpDocumentProcess` | `POST /gbp/processes/{id}/review/`, `GET .../export/` |
| RF-45 | 32 | `PaoPeriod` | `GET/POST/PATCH /gbp/pao/` |
| RF-46 | 6 | `Club` | `GET /clubs/?q=&faculty=&area=` |
| RF-47, RF-48 | 6, 7, 19 | `Club`, `Membership` | Serializers diferenciados |
| RF-49 | 33 | Todas | `GET /gbp/history/?pao=` |
| RF-50 | 14, 15 | `Student` | `GET/PATCH /students/me/`, `GET /students/me/history/` |
| RF-51 | 5 | `Notification` | `GET /notifications/` |
| RF-52 | — | Auditoría | Campos `reviewed_by`, `scanned_by_staff`, timestamps |
| — | **34** | `EventRegistration` | `GET /events/{id}/registrations/` |

---

## 20. Divergencias y deuda detectada

Inconsistencias reales entre la documentación previa, los datos y el código. **Resolverlas al construir el backend** — cada fila indica la decisión recomendada.

| # | Divergencia | Dónde | Decisión recomendada |
| :-- | :--- | :--- | :--- |
| 1 | El `README.md` describe **tres** roles predeterminados; `requirements.md` y los datos definen **cuatro** (incluyendo *Miembro*) | README §2.1 vs. `roles.json` | **Cuatro roles.** *Miembro* es el rol base sin permisos, necesario para RF-08 |
| 2 | El mock del README asigna al Miembro `role_id: 11`; `usuarios.json` usa `role_id: 10`, y el 11 es un rol personalizado | README §4.4 vs. `usuarios.json` | Usar **10** (`Miembro`). El 11 es *Encargado de Documentos* |
| 3 | `Club` en el README no incluye `faculty`, `status`, `interest_areas` ni `members_count`, pero los datos y el frontend sí los usan | README §4.1 vs. `clubes.json` | El modelo canónico de §7.2 es el correcto |
| 4 | `Event` en el README anida `administrative_data` (objetivo, ODS, aliados, medición de impacto); los datos reales lo omiten y aplanan `visibility`, `end_datetime`, `blocked_message`, `stats` | README §4.1 vs. `eventos.json` | Modelar los campos planos como obligatorios y `administrative_data` como bloque **opcional** (JSON o tabla 1:1). No perder los campos: son requisito de reportería a GBP |
| 5 | `registerScan()` no escribe `registration_id` ni `qr_token_validated`, pero el esquema de `EventAttendance` los exige | `data-service.js` vs. `asistencias.json` | En Django **son obligatorios**: la asistencia debe referenciar su inscripción y el token validado (RNF-12) |
| 6 | El Staff no se valida al escanear: `registerScan()` acepta cualquier `staffStudentId` | `data-service.js` | En backend, **exigir** que quien escanea esté en `EventStaff` del evento (RF-35) |
| 7 | `getVisibleEvents()` ignora el `studentId` y devuelve todos los eventos | `data-service.js` | Correcto por diseño (RF-31: los `MembersOnly` son visibles). Mantener, pero el **registro** sí se bloquea |
| 8 | `Club.members_count` y `Event.stats` están denormalizados en los `.json` | `clubes.json`, `eventos.json` | **Calcular en el servidor.** No persistir contadores |
| 9 | `Club.internal_documents` y el Staff viven embebidos / en `localStorage` | Fase 1 | Promover a tablas `ClubDocument` y `EventStaff` |
| 10 | **Pantalla 34 (Bitácora)** no está en el inventario de 33 pantallas ni en `pages_description.md`, y no tiene ID de formulario ni de visualización | `pages/lider/bitacora.html`, `js/pages/lider/bitacora.js` | Documentada aquí. **Deuda:** hoy toma `clubEvent[0]` (siempre el primer evento) sin selector; añadir selector de evento y estado vacío |
| 11 | `bitacora.html` conserva el `<title>` de otra pantalla ("Información del club") | `pages/lider/bitacora.html` | Corregir el título |
| 12 | `bitacora.js` no escapa los datos que inyecta en el HTML (no usa `esc()`) | `js/pages/lider/bitacora.js` | Usar `esc()` como el resto de las pantallas |
| 13 | El menú del líder añade "Bitacora" sin tilde | `js/app.js` | Corregir a "Bitácora" |
| 14 | La Fase 2 estaba definida sobre **FastAPI**; se construirá con **Django** | README §5.2, `requirements.md` | Actualizar README y requirements, o dejar constancia de la decisión. Ver §16.1 |
| 15 | El congelamiento automático por PAO (RF-20) y la expiración de QR (RF-37) **no existen** en Fase 1 | Fase 1 | Implementar como tareas programadas (§16.8). Son requerimientos exclusivos de F2 |
| 16 | RN-1 (un solo liderazgo) **no se valida** en ningún punto del código actual | `data-service.js` | Validar en `Membership.clean()` y en la asignación de líder |
| 17 | RN-7 (`manage_roles` restringido) se documenta pero no se aplica al crear roles | `js/pages/lider/roles.js` | Validar en el serializer de `Role` |
| 18 | Las notificaciones son de solo lectura: ningún flujo **crea** notificaciones nuevas | `data-service.js` | En Django, emitirlas desde señales de dominio (§16.8) |

---

## 21. Preguntas pendientes de definición

Ninguna bloqueó el diseño del frontend; **todas conviene resolverlas al cerrar la Fase 2**.

| ID | Pregunta | Impacto |
| :--- | :--- | :--- |
| **PPD-01** | No se ha especificado la **lista completa y oficial de facultades** de ESPOL sobre la que opera el filtro del catálogo | Único punto con efecto visible en el frontend. Se arranca con el catálogo provisional de 7 facultades (§7.3), ampliable |
| **PPD-02** | No se ha definido el **mecanismo de provisión de las cuentas de Administrador GBP** | Propio de la Fase 2. Propuesta: creación manual vía `django-admin` con `is_gbp_admin = True`; no hay auto-registro para GBP |
| **PPD-03** | No se ha definido el **comportamiento del escaneo de QR ante un fallo de conexión** durante el evento (modo degradado) | Propio de la Fase 4. Nota: RNF-11 declara que no se exige modo offline completo |
| **PPD-04** *(nuevo)* | La pantalla 34 (Bitácora) no tiene alcance definido: ¿es la bitácora de **un evento** seleccionable, de **todos** los eventos, o un log de acciones auditables del club (RF-52)? | Bloquea su especificación formal como pantalla del inventario |
| **PPD-05** *(nuevo)* | No está definido **quién marca `Under Review`** un trámite: ¿lo hace GBP explícitamente o al abrir el PDF? | Afecta la máquina de estado de §5.3 |

---

## 22. Glosario

| Término | Significado |
| :--- | :--- |
| **ESPOL** | Escuela Superior Politécnica del Litoral |
| **GBP** | Gerencia de Bienestar Politécnico. Entidad institucional que valida y audita los clubes |
| **PAO** | Período Académico Ordinario (semestre académico de ESPOL) |
| **SDG / ODS** | *Sustainable Development Goals* / Objetivos de Desarrollo Sostenible |
| **FIEC** | Facultad de Ingeniería en Electricidad y Computación |
| **FCNM** | Facultad de Ciencias Naturales y Matemáticas |
| **FIMCP** | Facultad de Ingeniería en Mecánica y Ciencias de la Producción |
| **FICT** | Facultad de Ingeniería en Ciencias de la Tierra |
| **FCSH** | Facultad de Ciencias Sociales y Humanísticas |
| **FCV** | Facultad de Ciencias de la Vida |
| **FADCOM** | Facultad de Arte, Diseño y Comunicación Audiovisual |
| **SAAC** | Sistema Académico central de ESPOL (fuera de alcance, RNF-09) |
| **Staff** | Miembro de un club con permiso **temporal**, ligado a un evento, para escanear códigos QR |
| **QR** | *Quick Response code*; credencial que valida la asistencia a un evento mediante un token opaco firmado |
| **Nómina** | Lista consolidada de miembros activos de un club en un PAO |
| **Trámite** | Envío documental de un club a GBP, con su ciclo de aprobación |
| **Overlay** | Capa de escritura simulada en `localStorage` usada en la Fase 1 |
| **CRUD** | *Create, Read, Update, Delete* |
| **JWT** | *JSON Web Token*; mecanismo de autenticación y autorización por token |
| **FOUC** | *Flash of Unstyled Content*; parpadeo evitado por `theme-init.js` |
| **RF / RNF** | Requerimiento Funcional / No Funcional |
| **RN** | Regla de Negocio (§6) |
| **PPD** | Pregunta Pendiente de Definición (§21) |

---

## Apéndice A — Checklist de construcción del backend Django

Lista de verificación derivada de todo el documento. Un ítem marcado significa **implementado y probado**.

**Modelos y datos**
- [ ] 12 modelos creados (§7.2), incluidos `ClubDocument` y `EventStaff` como tablas propias
- [ ] Las 15 restricciones de integridad de §7.4 aplicadas como `constraints` de base de datos
- [ ] Todos los enums como `TextChoices` con valor inglés y etiqueta española (§18)
- [ ] `members_count` y `stats` calculados, no almacenados
- [ ] Fixtures de §17 cargados y reproduciendo el estado de la Fase 1

**Autenticación**
- [ ] `Student` como `AUTH_USER_MODEL` con `enrollment` como `USERNAME_FIELD`
- [ ] Validación de dominio `@espol.edu.ec` en el registro
- [ ] Verificación de correo por enlace firmado
- [ ] JWT emitido y refrescable
- [ ] Rol de aplicación **derivado** (no almacenado) y expuesto en `/auth/me/`
- [ ] Activación diferida del líder al registrarse una matrícula con club `Pending Leader`

**Reglas de negocio**
- [ ] RN-1 — un solo liderazgo activo por estudiante
- [ ] RN-2 — sin `Pending` duplicada ni postulación siendo miembro; reaplicación inmediata permitida
- [ ] RN-3 — serializers diferenciados; ningún no-miembro recibe la nómina
- [ ] RN-4 — congelamiento automático al `end_date` del PAO
- [ ] RN-5 — feedback obligatorio en ambos rechazos (solicitud y trámite)
- [ ] RN-6 — `UNIQUE(event, student)` + `qr_status = Used`, con transacción y bloqueo
- [ ] RN-7 — `manage_roles` restringido a Presidente/a

**Comportamiento**
- [ ] Los 4 roles predeterminados se crean automáticamente al dar de alta un club
- [ ] Aprobar una solicitud crea la `Membership` con rol Miembro y las fechas del PAO activo
- [ ] Un formulario con respuestas no puede editarse: se versiona
- [ ] `MembersOnly` visible para todos, registro bloqueado para no-miembros
- [ ] Solo el Staff asignado al evento puede escanear
- [ ] Un trámite `Submitted` no admite edición por el club
- [ ] Activar un PAO cierra los demás
- [ ] Nada se borra físicamente: todo por cambio de estado

**Procesos automáticos**
- [ ] Congelamiento de membresías vencidas (idempotente)
- [ ] Expiración de membresías no renovadas
- [ ] Expiración de `qr_token` al superar `end_datetime`
- [ ] Marcado de `NoShow` tras finalizar el evento
- [ ] Emisión de notificaciones ante cada cambio de estado

**Entrega**
- [ ] Exportación `.xlsx` y `.pdf`; carga limitada a esos formatos
- [ ] `js/data-service.js` reescrito contra la API, **sin tocar ninguna pantalla**
- [ ] Divergencias de §20 resueltas o registradas como decisión consciente

---

*Documento maestro de ESPOLCLUB. Consolida `README.md`, `requirements.md`, `frontend_design.md`, `pages_description.md`, los 12 archivos de datos simulados y el código de la Fase 1. Emitido para la construcción del backend en Django.*
