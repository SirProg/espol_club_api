# ESPOLCLUB — Estructura Lógica de Negocio (Fase 2)

**Documento derivado de:** `MASTER.md`
**Propósito:** definir el **dominio** —agregados, invariantes, casos de uso, autorización y procesos— **antes** de escribir `models.py`.
**Alcance:** ninguna línea de código de implementación. Este documento se traduce a Django en el paso siguiente.
**Fecha:** 2026-08-11

---

## 0. Cómo se relaciona con MASTER.md

`MASTER.md` describe **qué** hace el sistema (57 RF, 13 RNF, 12 entidades, 34 pantallas). Este documento define **cómo se organiza la lógica** que lo sostiene: quién es dueño de cada invariante, qué operación puede romper qué regla, y en qué capa se detiene cada violación.

Donde este documento contradice a `MASTER.md`, gana este documento y la contradicción queda registrada explícitamente en §4 (decisiones D-01…D-14) y §12.

| Si buscas… | Ve a |
| :--- | :--- |
| Cómo se parten las apps y por qué | §2 |
| Qué entidad protege qué regla | §3 |
| Qué cambia respecto del modelo de MASTER §7.2 | §4 |
| Transiciones legales de cada estado | §5 |
| La lista de operaciones del backend | §6 |
| Dónde se aplica cada invariante (BD/servicio/serializer) | §7 |
| Quién puede hacer qué | §8 |
| Qué dispara notificaciones | §9 |
| Tareas programadas | §10 |
| Qué ve cada quién | §11 |
| Árbol de módulos Django | §13 |
| Orden de construcción | §14 |

---

## 1. Principios de la capa de negocio

**P-1 — La regla vive en el dominio, no en la vista.**
Ninguna regla de negocio se implementa en un `ViewSet`. Las vistas orquestan: autentican, deserializan, llaman un servicio y serializan la respuesta. Esto es obligatorio porque cada operación debe funcionar idéntica desde tres entradas distintas (panel web, app móvil, `django-admin`, y `management commands`).

**P-2 — Triple defensa por invariante.**
Cada invariante crítico se defiende en tres niveles: *constraint de BD* (última línea, resiste concurrencia), *servicio de dominio* (mensaje de negocio legible), *serializer* (feedback temprano al usuario). Un invariante que solo vive en el serializer no existe.

**P-3 — Comandos y consultas separados.**
`services/` contiene **comandos** (mutan estado, transaccionales, emiten eventos). `selectors/` contiene **consultas** (leen, nunca mutan, resuelven privacidad). Ninguna vista consulta el ORM directamente.

**P-4 — Nada se borra.**
No hay `DELETE` físico sobre entidades con historia (membresías, solicitudes, inscripciones, asistencias, trámites, clubes, estudiantes). Se cambia de estado. El borrado real solo se permite sobre entidades **sin descendencia** (rol sin uso, formulario sin respuestas, evento sin inscripciones, documento de club), y siempre condicionado a una verificación previa explícita.

**P-5 — El estado se deriva siempre que se pueda.**
No se persiste lo que se puede calcular: `members_count`, `stats` de evento, edad del estudiante, rol de aplicación (Estudiante/Miembro/Líder/GBP). La única excepción son los **snapshots deliberados** de §4 (D-05, D-09), que existen para poder expresar un invariante en la BD y están documentados como tales.

**P-6 — El tiempo es un actor.**
Cuatro transiciones del sistema no las dispara ningún usuario, sino el calendario: congelamiento de membresías, expiración de membresías, expiración de QR y marcado de `NoShow`. Se modelan como comandos idempotentes de primera clase (§10), no como efectos colaterales de una lectura.

**P-7 — El PAO es el reloj del negocio.**
La vigencia de casi todo (membresías, nóminas, trámites, histórico) se ancla a un `PaoPeriod`. Por eso el período académico es un contexto propio del que dependen los demás (§2), no un detalle de GBP.

---

## 2. Mapa de contextos (apps) y dependencias

### 2.1 Corrección a MASTER §16.2

MASTER propone `gbp/` como dueño de `PaoPeriod` y declara el criterio de frontera *"`gbp` conoce `clubs`"*. Pero `Membership` (en `clubs`) tiene FK a `PaoPeriod` (en `gbp`), lo que produce **dependencia circular** `clubs ⇄ gbp`.

> **Decisión:** se extrae `PaoPeriod` a un contexto propio **`academic`** (calendario académico institucional). No pertenece a GBP: GBP lo *administra*, pero el negocio entero lo *consume*. Con esto todas las dependencias quedan en un solo sentido.

### 2.2 Contextos

| # | App | Responsabilidad | Depende de |
| :-- | :--- | :--- | :--- |
| 1 | `accounts` | Identidad, registro, verificación, JWT, derivación del rol de aplicación | — |
| 2 | `academic` | `PaoPeriod`: calendario, período activo, apertura/cierre | — |
| 3 | `catalogs` | Facultades, áreas de interés, tipos de campo, formatos permitidos | — |
| 4 | `clubs` | `Club`, `ClubDocument`, `Role`, `Membership`, liderazgo, nómina | `accounts`, `academic`, `catalogs` |
| 5 | `dynamicforms` | `Form`: esquema, versionado, validación de respuestas contra esquema | `clubs`, `catalogs` |
| 6 | `applications` | `MembershipApplication`: postulación, resolución, alta de membresía | `clubs`, `dynamicforms`, `academic` |
| 7 | `events` | `Event`, `EventRegistration`, `EventStaff`, `EventAttendance`, ciclo QR | `clubs`, `dynamicforms` |
| 8 | `gbp` | `GbpDocumentProcess`, buzón, revisión, exportaciones, alta de clubes | `clubs`, `academic` |
| 9 | `notifications` | `Notification`, suscripción a eventos de dominio | (nadie la conoce; ella escucha) |

> `dynamicforms` en vez de `forms`: `forms` colisiona con `django.forms` y produce importaciones ambiguas.

### 2.3 Grafo de dependencias (acíclico)

```
        accounts      academic      catalogs
            │             │             │
            └──────┬──────┴──────┬──────┘
                   ▼             ▼
                 clubs ◄─────────┘
                   │
        ┌──────────┼──────────┬──────────┐
        ▼          ▼          ▼          ▼
 dynamicforms   events   applications   gbp
        │          │          │          │
        └──────────┴────┬─────┴──────────┘
                        ▼
                 notifications        (solo escucha señales)
```

**Regla de importación:** un contexto solo importa hacia arriba en el grafo. `notifications` no es importado por nadie: se suscribe a los eventos de dominio de §9. Si un contexto necesita algo de un hermano, se resuelve por evento de dominio, nunca por import cruzado.

---

## 3. Agregados, raíces e invariantes

Un **agregado** es la unidad de consistencia transaccional: se carga, se valida y se guarda como un todo. Las referencias entre agregados son por identidad, y las reglas que cruzan dos agregados suben a un **servicio de dominio**.

| Agregado (raíz) | Contiene | Identidad | Invariantes que protege |
| :--- | :--- | :--- | :--- |
| **Student** | — | `enrollment` (natural), `id` (técnica) | Matrícula única, correo único e institucional, fecha de nacimiento no futura |
| **PaoPeriod** | — | `pao_period` (`2026-I`) | `end_date > start_date`; **un solo `Active`** |
| **Club** | `ClubDocument[]`, `Role[]` | `id` | ≥1 área de interés; nombre de rol único en el club; los 4 roles por defecto existen y no se borran; coherencia `status` ↔ liderazgo |
| **Membership** | — | `id` | `role.club == membership.club`; unicidad `(student, club, pao)`; vigencia copiada del PAO |
| **Form** | campos (JSON) | `id` | ≥1 campo; opciones ≥2 en `select/radio/checkbox`; inmutabilidad si tiene respuestas; versión monotónica por familia |
| **MembershipApplication** | respuestas (JSON) | `id` | Feedback obligatorio al rechazar; respuestas válidas contra su `form`; una sola `Pending` por (student, club) |
| **Event** | `EventStaff[]`, `EventRegistration[]` | `id` | Fin posterior al inicio; límite de registro ≤ inicio; staff ⊆ miembros activos del club |
| **EventAttendance** | — | `id` | Unicidad `(event, student)`; inmutable tras crearse; `scanned_at` del servidor |
| **GbpDocumentProcess** | — | `id` | Congelado tras `Submitted`; feedback obligatorio al rechazar |
| **Notification** | — | `id` | — (append-only; solo `read` muta) |

### 3.1 Reglas que **no** caben en un agregado

Estas cruzan agregados y por tanto viven en servicios de dominio, no en un `clean()` de modelo:

| Regla | Por qué cruza | Servicio dueño |
| :--- | :--- | :--- |
| **RN-1** exclusividad de liderazgo | Compara membresías de **clubes distintos** del mismo estudiante | `clubs.services.leadership` |
| **RN-2** postulación única | Cruza `MembershipApplication` × `Membership` | `applications.services.apply` |
| **RN-3** privacidad de nómina | Es una política de lectura, no un estado | `clubs.selectors` + policies (§11) |
| **RN-4** caducidad por PAO | Cruza `Membership` × `PaoPeriod` × reloj | `academic`/`clubs` command programado |
| **RN-6** no reescaneo | Cruza `EventRegistration` × `EventAttendance` bajo concurrencia | `events.services.attendance` |
| Aprobación → alta de membresía | Cruza `applications` × `clubs` × `academic` | `applications.services.resolve` |
| Activación diferida del líder | Cruza `accounts` × `clubs` | evento `student.registered` → handler en `clubs` |

---

## 4. Decisiones sobre el modelo lógico

Refinamientos y correcciones sobre `MASTER.md` §7.2 / §16.3. Cada uno tiene motivo; ninguno es cosmético.

---

**D-01 · El líder pendiente debe sobrevivir como matrícula, no como FK.**

MASTER §16.3 modela `Club.leader = FK(Student, null=True)`. Eso **pierde la información** del caso `Pending Leader`: el club 4 apunta a la matrícula `202099777`, que **no tiene cuenta**. Sin guardarla no puede cumplirse RF-12 (activar el liderazgo cuando esa matrícula se registre).

> **Decisión:** `Club` conserva **dos** campos con roles distintos:
> - `leader_enrollment` — texto, matrícula **asignada por GBP**. Fuente de verdad del *compromiso institucional*. Puede no corresponder a ninguna cuenta.
> - `leader` — FK a `Student`, nulable. Vínculo **resuelto**. Se llena cuando existe la cuenta.
>
> **Invariante de coherencia:**
> `status = Active` ⟺ `leader IS NOT NULL` **y** existe `Membership(student=leader, club, status=Active, role.is_leadership=True)`.
> `status = Pending Leader` ⟺ `leader IS NULL` (con `leader_enrollment` posiblemente presente).

---

**D-02 · Se elimina el ciclo `Form ⇄ Event`.**

MASTER define `Form.event_id → Event` **y** `Event.registration_form_id → Form`. Son dos aristas para la misma relación: ciclo de FKs y dos fuentes de verdad que pueden divergir (y que rompen el orden de `loaddata` en las fixtures).

> **Decisión:** la relación se declara **solo** como `Form.event` (nulable; obligatoria si `form_type = Event`).
> `Event.registration_form` desaparece como columna y se convierte en **propiedad derivada**: el `Form` de tipo `Event` con `is_active=True` de mayor `version` para ese evento.
> Semántica preservada: *"sin formulario activo = sin registro abierto"* equivale exactamente al `registration_form_id = NULL` original.

---

**D-03 · El formulario tiene familia, versión y vigencia.**

El versionado de RF-24 necesita un concepto que MASTER no nombra: la **familia de formulario**, es decir la tupla `(club, form_type, event)`. La versión es monotónica *dentro de la familia*, y solo una versión de la familia está activa.

> **Decisión:**
> - `version` = `max(version de la misma familia) + 1`, asignado por el servidor dentro de la transacción.
> - Crear la versión N+1 **desactiva** la N (`is_active=False`) en el mismo commit.
> - Un `Form` **con respuestas** es inmutable: `PATCH` responde `409` y expone la acción "crear nueva versión".
> - Las respuestas ya emitidas conservan su `form_id` original: el histórico se lee siempre contra el esquema con el que se llenó.

---

**D-04 · `MembershipApplication` necesita rastro de auditoría.**

RF-52 exige registrar *"quién aprobó/rechazó y cuándo"*, pero la entidad de MASTER §7.2 no tiene esos campos: solo `status` y `leader_feedback`.

> **Decisión:** se agregan `resolved_by` (FK `Student`, nulable), `resolved_at` (datetime, nulable).
> **Invariante:** `status != Pending` ⟹ ambos poblados.
> Se agrega también `created_at`/`updated_at` a **toda** entidad mutable del sistema (regla transversal).

---

**D-05 · `Membership` guarda snapshot de liderazgo y su origen.**

Dos necesidades distintas apuntan al mismo cambio:
1. RN-1 (un solo liderazgo activo) requiere leer `role.is_leadership`, que vive en **otra tabla** — y ningún motor permite un índice único que cruce tablas (§7.3).
2. La trazabilidad de la nómina requiere saber de dónde salió cada membresía (solicitud aprobada, renovación, asignación de GBP).

> **Decisión:**
> - `is_leadership` — booleano **copiado** del rol al asignarlo. Snapshot deliberado, no denormalización accidental.
>   **Regla de resincronización:** cambiar `Membership.role`, o cambiar `Role.is_leadership`, obliga a reescribir el snapshot de todas las membresías afectadas en la misma transacción.
> - `origin` — enum `Application | Renewal | LeaderAssignment | Seed`.
> - `source_application` — FK nulable a `MembershipApplication`.

---

**D-06 · `EventAttendance` duplica `event` y `student` a propósito.**

Ambos son derivables de `registration`. Se duplican porque el invariante RN-6 se expresa como `UNIQUE(event_id, student_id)` **en la propia tabla de asistencia**, que es la única defensa real contra dos escaneos concurrentes.

> **Decisión:** se mantiene la duplicación, poblada **por el servidor** desde `registration` dentro de la transacción de escaneo. Nunca desde el cliente.
> Se cierra la divergencia §20.5 de MASTER: `registration` y `qr_token_validated` son **obligatorios**.

---

**D-07 · Los datos administrativos del evento son un bloque opcional 1:1.**

Divergencia §20.4: el README anida `administrative_data` (objetivo, ODS, responsable, aliados, medición de impacto) y los datos de Fase 1 lo omiten.

> **Decisión:** tabla propia `EventAdministrativeData` en relación **1:1 opcional** con `Event`. No JSON: son los campos que alimentan la reportería a GBP y deben poder filtrarse y exportarse. Su ausencia no bloquea la creación del evento.

---

**D-08 · La ventana de escaneo es explícita.**

RF-35 dice que el escaneo vale *"solo durante ese evento"*, sin definir el intervalo.

> **Decisión:** ventana `[inicio − SCAN_LEAD_MINUTES, end_datetime + SCAN_GRACE_MINUTES]`, con `SCAN_LEAD_MINUTES = 120` y `SCAN_GRACE_MINUTES = 30` como parámetros de configuración, no constantes incrustadas. Fuera de la ventana el escaneo se rechaza aunque el staff esté asignado y el QR sea válido.

---

**D-09 · Snapshots de nómina para el trámite GBP.**

RF-41 congela el trámite enviado, pero la **nómina** que lo respalda es una consulta viva: si un miembro se revoca al día siguiente, el PDF aprobado deja de corresponder a los datos.

> **Decisión:** `GbpDocumentProcess` guarda `roster_snapshot` (JSON, inmutable) con la nómina consolidada al momento del envío. Es evidencia auditable, no una vista. Se completa con `submitted_by` (FK `Student`) y `reviewed_at`.

---

**D-10 · `Notification` transporta referencia, no solo texto.**

MASTER modela `type`, `message`, `date`, `read`. Con eso el centro de notificaciones no puede enlazar al objeto que cambió.

> **Decisión:** se agregan `target_type` (str) y `target_id` (int), nulables, y `club` (FK nulable) para poder filtrar por club. El `message` sigue siendo texto ya renderizado en español (RNF-10: la traducción vive en presentación, y la notificación **es** presentación).

---

**D-11 · El rol de aplicación se deriva; se cachea por request.**

Derivar el rol en cada chequeo de permiso implica consultar membresías repetidamente.

> **Decisión:** se resuelve **una vez por request** en middleware/propiedad cacheada, produciendo un objeto de contexto `{ app_role, gbp_admin, memberships: {club_id: (role_id, permissions)} }`. Las clases de permiso leen ese contexto, no la BD. Nada de esto se persiste.

---

**D-12 · Precedencia de roles de aplicación.**

Un estudiante puede ser simultáneamente líder de un club y miembro de otro. El rol de aplicación es el **máximo** alcanzado, y solo determina el "hogar" de navegación (MASTER §11); **no** otorga permisos por sí mismo.

> **Decisión — orden de precedencia:** `GBP Admin` > `Líder de Club` > `Miembro del Club` > `Estudiante Politécnico`.
> `GBP Admin` es excluyente: una cuenta institucional no participa en clubes.
> Los permisos efectivos **siempre** se resuelven por club vía `Membership.role.permissions`, nunca por el rol de aplicación.

---

**D-13 · `Role` se desactiva; no siempre se borra.**

`isRoleInUse()` bloquea el borrado, pero deja al club sin forma de retirar un rol obsoleto que tuvo miembros históricos.

> **Decisión:** `Role` gana `is_active` (bool). Borrado físico solo si nunca tuvo membresías; en caso contrario se desactiva: no se puede asignar, pero las membresías históricas conservan su rol legible. Los 4 roles `is_default` no se borran ni se desactivan.

---

**D-14 · El identificador de PAO es validado, no libre.**

`pao_period` es PK de texto y clave de negocio en todo el sistema.

> **Decisión:** formato normalizado `^\d{4}-(I|II)$`, validado en el modelo. Se agrega `sequence` (entero derivado del identificador, p. ej. `2026-I → 20261`) para poder **ordenar cronológicamente** los períodos, que es lo que necesita la regla de expiración (§10) y el histórico (RF-49). Ordenar por texto sería incorrecto en cuanto exista `2026-II` vs `2026-I`.

---

## 5. Ciclos de vida y máquinas de estado

Formato: `Estado origen → Estado destino [disparador] {guarda} ⇒ efectos`.

### 5.1 `Club.status`

| # | Transición | Disparador | Guarda | Efectos |
| :-- | :--- | :--- | :--- | :--- |
| C1 | *(alta)* → `Active` | GBP crea club | La matrícula del líder tiene cuenta | Crea 4 roles por defecto; crea `Membership` Presidente/a en el PAO activo; verifica RN-1 sobre ese estudiante |
| C2 | *(alta)* → `Pending Leader` | GBP crea club | La matrícula **no** tiene cuenta | Crea 4 roles por defecto; club en solo lectura |
| C3 | `Pending Leader` → `Active` | Registro del estudiante con esa matrícula (RF-12) | Matrícula coincide y verificada | Vincula `leader`; crea `Membership` Presidente/a; notifica |
| C4 | `Pending Leader` → `Active` | GBP asigna líder | La matrícula tiene cuenta y no lidera otro club (RN-1) | Igual a C3 |
| C5 | `Active` → `Pending Leader` | GBP revoca líder (RF-13) | — | `Membership` directiva → `Revoked`; `leader = NULL`; club en solo lectura; notifica |

> **Club en solo lectura:** con `status = Pending Leader` se rechazan **todas** las operaciones de escritura del club (eventos, formularios, roles, documentos, resolución de solicitudes, trámites). Las lecturas siguen disponibles. Se implementa como una única *policy* transversal, no repetida por vista.

### 5.2 `Membership.status`

| # | Transición | Disparador | Guarda | Efectos |
| :-- | :--- | :--- | :--- | :--- |
| M1 | *(alta)* → `Active` | Aprobación de solicitud / renovación / asignación de líder | Existe PAO activo; no viola RN-1 ni la unicidad `(student, club, pao)` | Copia `valid_from/until` del PAO; fija snapshot `is_leadership` |
| M2 | `Active` → `Frozen` | Proceso diario | `valid_until < hoy` | Nómina congelada como evidencia; permisos suspendidos |
| M3 | `Frozen` → `Expired` | Proceso diario | El PAO está `Closed` y **no existe** membresía del mismo `(student, club)` en un PAO de `sequence` mayor | Cierre definitivo del vínculo |
| M4 | `Active`\|`Frozen` → `Revoked` | Líder da de baja / GBP revoca liderazgo | Un líder no puede autorrevocarse; solo GBP retira liderazgo | Libera RN-1 si era directiva; notifica |
| M5 | `Frozen` → *(nueva `Active`)* | Renovación de nómina (RF-21) | PAO activo ≠ PAO de origen | **No muta la congelada**: crea una fila nueva en el PAO activo (`origin = Renewal`) |

> **M5 es la regla más fácil de implementar mal.** Renovar **no** reactiva la membresía vieja: la histórica permanece `Frozen` como evidencia del PAO anterior. Se crea una membresía nueva. Esto es lo que hace que RF-49 (histórico por PAO) sea consultable.

### 5.3 `MembershipApplication.status`

| # | Transición | Disparador | Guarda | Efectos |
| :-- | :--- | :--- | :--- | :--- |
| A1 | *(alta)* → `Pending` | Estudiante postula | RN-2: sin `Pending` previa en ese club y sin membresía activa; formulario activo; respuestas válidas | Notifica al líder |
| A2 | `Pending` → `Approved` | Líder resuelve | Existe PAO activo; club `Active`; permiso `manage_members` | Congela el registro; **crea `Membership`** con rol *Miembro*; `resolved_by/at`; notifica |
| A3 | `Pending` → `Rejected` | Líder resuelve | `leader_feedback` no vacío (RN-5) | Congela el registro; `resolved_by/at`; notifica; habilita reaplicación inmediata (RF-29) |

Estados terminales: `Approved` y `Rejected` no admiten transición posterior. Reaplicar crea una **fila nueva**.

### 5.4 `EventRegistration` — dos ejes independientes

```
attendance_status:  Registered ──[escaneo válido]──► Attended
                               └──[proceso, fin del evento]──► NoShow

qr_status:          Active ──[escaneo válido]──► Used
                           └──[proceso, end_datetime]──► Expired
```

| # | Transición | Guarda | Efectos |
| :-- | :--- | :--- | :--- |
| Q1 | `Active` → `Used` + `Registered` → `Attended` | Token existe, `qr_status = Active`, escáner en `EventStaff` del evento, dentro de la ventana D-08 | Crea `EventAttendance` (inmutable); ambos ejes avanzan en la **misma transacción** |
| Q2 | `Active` → `Expired` | Proceso horario; `now > end_datetime` | Token inutilizable |
| Q3 | `Registered` → `NoShow` | Proceso; evento finalizado sin asistencia | Alimenta la métrica inscritos vs. asistentes |

**Ejes independientes, no redundantes:** `qr_status` describe la *credencial*; `attendance_status` describe la *participación*. Un QR `Expired` con `attendance_status = NoShow` es un estado normal y esperado.

### 5.5 `GbpDocumentProcess.status`

| # | Transición | Disparador | Guarda | Efectos |
| :-- | :--- | :--- | :--- | :--- |
| G1 | *(alta)* → `Submitted` | Líder envía | Permiso `submit_gbp_reports`; PDF válido; PAO indicado | Congela edición; **fija `roster_snapshot`** (D-09); notifica a GBP |
| G2 | `Submitted` → `Under Review` | **Acción explícita de GBP** (PPD-05) | Es admin GBP | Fija `reviewed_by`; el trámite queda tomado |
| G3 | `Under Review` → `Approved` | GBP resuelve | — | `reviewed_at`; notifica al club |
| G4 | `Under Review` → `Rejected` | GBP resuelve | `review_feedback` no vacío (RN-5) | Reabre: el club puede enviar un trámite corregido; notifica |

> **PPD-05 resuelta:** `Under Review` se marca **explícitamente** por GBP ("tomar trámite"), no al abrir el PDF. Motivo: deja `reviewed_by` poblado con quién asumió la revisión, y evita que una simple descarga cambie el estado del negocio.
> `Submitted → Approved` directo **no existe**: obliga el paso por `Under Review` para que siempre haya un responsable identificable (RF-52).

### 5.6 `PaoPeriod.status`

| # | Transición | Guarda | Efectos |
| :-- | :--- | :--- | :--- |
| P1 | *(alta)* → `Closed` | `end_date > start_date`, identificador válido y único | Período creado, inerte |
| P2 | `Closed` → `Active` | Solo GBP | **Cierra todos los demás** en la misma transacción (invariante I-08) |
| P3 | `Active` → `Closed` | Activación de otro período | Habilita M3 (expiración de membresías no renovadas) |

---

## 6. Catálogo de casos de uso

La superficie de operaciones del backend. Cada caso de uso es **una función de servicio, transaccional**, que traduce una operación del contrato de MASTER §14. Convención: `CU-<contexto><n>`.

Cada fila declara: **Actor** · **Precondiciones** (fallan con error de negocio) · **Efectos** · **Evento de dominio emitido**.

### 6.1 `accounts`

| ID | Caso de uso | Actor | Precondiciones | Efectos | Evento |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CU-AC1 | Registrar cuenta | Anónimo | Correo `@espol.edu.ec`; matrícula única; correo único; fecha nac. no futura; contraseñas coinciden | Crea `Student` no verificado; envía enlace firmado | — |
| CU-AC2 | Verificar correo | Anónimo con token | Token válido y no expirado | `is_verified = True` | `student.verified` → dispara C3 |
| CU-AC3 | Iniciar sesión | Anónimo | Credenciales válidas; cuenta verificada | Emite par JWT | — |
| CU-AC4 | Refrescar / recuperar contraseña | Anónimo | Flujo estándar | — | — |
| CU-AC5 | Resolver sesión (`/auth/me`) | Autenticado | — | Devuelve rol derivado (D-12), club liderado, permisos por club | — |
| CU-AC6 | Editar perfil propio | Estudiante (sí mismo) | Solo `description`, `skills`, `social_media`; URLs válidas | Actualiza | — |
| CU-AC7 | Provisionar admin GBP | Operador del sistema | Vía `management command` (PPD-02) | Crea `Student` con `is_gbp_admin` | — |

### 6.2 `academic`

| ID | Caso de uso | Actor | Precondiciones | Efectos | Evento |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CU-PA1 | Crear período | GBP | Formato `^\d{4}-(I\|II)$`; único; `end > start` | Crea `Closed` | — |
| CU-PA2 | Editar período | GBP | `end > start`; sin solapamiento con otros períodos | Actualiza | — |
| CU-PA3 | Activar período | GBP | El período existe | Cierra los demás; este pasa a `Active` (P2) | `pao.activated` |
| CU-PA4 | Consultar activo | Cualquiera | — | Devuelve el `Active` o error de configuración si no hay ninguno | — |

> **Precondición sistémica:** varias operaciones (aprobar solicitud, renovar nómina, alta de club con líder) **requieren** un PAO activo. Sin él fallan con un error de configuración explícito, no con un `500`.

### 6.3 `clubs`

| ID | Caso de uso | Actor | Precondiciones | Efectos | Evento |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CU-CL1 | Dar de alta un club | GBP | Nombre, acrónimo, descripción, ubicación, ≥1 área del catálogo, matrícula de líder | C1 o C2 según exista la cuenta; **crea los 4 roles por defecto** | `club.created` |
| CU-CL2 | Editar info del club | `manage_club_info` | Club `Active`; ≥1 área | Actualiza | — |
| CU-CL3 | Subir documento | `manage_documents` | `.pdf` verificado por extensión **y** content-type | Crea `ClubDocument` | — |
| CU-CL4 | Cambiar visibilidad de documento | `manage_documents` | — | Alterna `is_public` (RF-16) | — |
| CU-CL5 | Eliminar documento | `manage_documents` | — | Borrado físico permitido (sin descendencia) | — |
| CU-CL6 | Crear rol personalizado | `manage_roles` | Nombre único en el club; **RN-7**: `manage_roles` solo otorgable si `is_leadership` y por Presidente/a | Crea `Role` | — |
| CU-CL7 | Editar rol | `manage_roles` | No se alteran los flags de los 4 por defecto; RN-7 | Actualiza; **resincroniza snapshots** (D-05) | — |
| CU-CL8 | Retirar rol | `manage_roles` | No `is_default`; borra si nunca tuvo uso, si no desactiva (D-13) | Borra o desactiva | — |
| CU-CL9 | Cambiar rol de una membresía | `manage_members` | `role.club == membership.club`; **RN-1** si el destino es directivo | Actualiza rol y snapshot | `membership.role_changed` |
| CU-CL10 | Dar de baja a un miembro | `manage_members` | No se puede revocar al líder desde aquí (eso es CU-CL13) | `Revoked` (M4) | `membership.revoked` |
| CU-CL11 | Consultar nómina por PAO | Miembro / GBP | RN-3 | Lista membresías del período | — |
| CU-CL12 | Renovar nómina | `manage_members` | PAO activo ≠ PAO origen; ≥1 miembro; idempotente por unicidad | Crea membresías `Active` (M5) | `membership.renewed` |
| CU-CL13 | Revocar líder | GBP | Club `Active` | C5 | `club.leader_revoked` |
| CU-CL14 | Asignar líder | GBP | La matrícula no lidera otro club (RN-1) | C4, o queda `Pending Leader` si no hay cuenta | `club.leader_assigned` |
| CU-CL15 | Consultar catálogo | Autenticado | — | Filtra por `q`, `faculty`, `area`; **solo contador** de miembros (RN-3) | — |

### 6.4 `dynamicforms`

| ID | Caso de uso | Actor | Precondiciones | Efectos | Evento |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CU-FO1 | Crear formulario | `manage_forms` | ≥1 campo; `field_id` únicos; ≥2 opciones en `select/radio/checkbox`; si `form_type=Event` exige `event` del mismo club | Calcula `version` (D-03); desactiva la versión previa de la familia | `form.published` |
| CU-FO2 | Editar formulario | `manage_forms` | **Solo si no tiene respuestas**; si las tiene → `409` con indicación de versionar | Actualiza en sitio | — |
| CU-FO3 | Desactivar formulario | `manage_forms` | — | `is_active = False`; cierra el registro asociado | — |
| CU-FO4 | Eliminar formulario | `manage_forms` | Sin respuestas | Borrado físico | — |
| CU-FO5 | Obtener esquema para render | Autenticado | Formulario activo | Devuelve campos ordenados por `order` | — |
| CU-FO6 | **Validar respuestas contra esquema** | *(servicio interno)* | Cada `field_id` existe en el esquema; `required` cumplidos; valores de `select/radio/checkbox` dentro de `options`; `validation` (p. ej. `max_length`) respetado | Devuelve respuestas normalizadas o error por campo | — |

> **CU-FO6 es el servicio compartido más importante del sistema:** lo consumen tanto la postulación (CU-AP1) como la inscripción a evento (CU-EV7). Sin él, un cliente malicioso puede enviar respuestas arbitrarias. Se implementa **una sola vez**, en `dynamicforms`.

### 6.5 `applications`

| ID | Caso de uso | Actor | Precondiciones | Efectos | Evento |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CU-AP1 | Postular a un club | Estudiante | **RN-2** (sin `Pending`, sin membresía activa); club `Active`; formulario de membresía activo; CU-FO6 OK | Crea `Pending` (A1) | `application.submitted` |
| CU-AP2 | Consultar elegibilidad | Estudiante | — | `{allowed, reason}` con los mensajes canónicos de MASTER §12 | — |
| CU-AP3 | Listar bandeja | `manage_members` | RN-3 | Solicitudes del club con respuestas resueltas contra su esquema | — |
| CU-AP4 | Aprobar | `manage_members` | Estado `Pending`; PAO activo; club `Active` | A2 + **alta de `Membership`** rol *Miembro* (`origin=Application`) | `application.approved` |
| CU-AP5 | Rechazar | `manage_members` | Estado `Pending`; feedback no vacío (**RN-5**) | A3 | `application.rejected` |

> **CU-AP4 es transaccionalmente crítica:** resolver la solicitud y crear la membresía ocurren en el **mismo commit**. Una solicitud `Approved` sin membresía es un estado corrupto no recuperable automáticamente.

### 6.6 `events`

| ID | Caso de uso | Actor | Precondiciones | Efectos | Evento |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CU-EV1 | Crear evento | `manage_events` | Club `Active`; `end_datetime` > inicio; `registration_deadline` ≤ inicio | Crea evento | `event.created` |
| CU-EV2 | Editar evento | `manage_events` | Mismas guardas de fechas | Actualiza | — |
| CU-EV3 | Eliminar evento | `manage_events` | **Sin inscripciones** | Borrado físico | — |
| CU-EV4 | Listar eventos visibles | Autenticado | — | **Todos**, incluidos `MembersOnly` (RF-31: visibles, registro bloqueado) | — |
| CU-EV5 | Consultar elegibilidad de registro | Autenticado | Cadena en orden: ya inscrito → sin formulario → `MembersOnly` y no miembro → fecha límite excedida | `{can_register, reason}` con mensajes canónicos | — |
| CU-EV6 | Asignar staff | `manage_events` | Cada estudiante es **miembro activo** del club del evento | Reemplaza la asignación completa | `event.staff_changed` |
| CU-EV7 | Inscribirse | Estudiante | CU-EV5 permite; CU-FO6 OK; unicidad `(event, student)` | Crea inscripción; **emite `qr_token` firmado**; `Active`/`Registered` | `event.registered` |
| CU-EV8 | Ver credencial | Estudiante (dueño) | — | Devuelve el token y datos del evento | — |
| CU-EV9 | **Escanear QR** | Staff del evento | Cadena: token no vacío → existe → no `Used`/`Attended` → no `Expired` → escáner en `EventStaff` → dentro de la ventana D-08 | Q1: crea `EventAttendance`, marca `Used`/`Attended`, `scanned_at` del servidor | `attendance.registered` |
| CU-EV10 | Bitácora de inscritos | `manage_events` | Evento del club; **con selector de evento** (PPD-04) | Lista inscritos: nombre, matrícula, fecha, estado de asistencia | — |
| CU-EV11 | Métricas del evento | `manage_events` | — | `registered` / `attended` **calculados** | — |

**CU-EV9 en detalle** (la operación más sensible del sistema):

```
1. Abrir transacción.
2. SELECT ... FOR UPDATE sobre EventRegistration por qr_token.   ← bloqueo de fila
3. Cadena de guardas, en este orden exacto, cada una con su mensaje canónico:
   token vacío        → "Ingresa o escanea un código."
   no existe          → "Credencial no reconocida."
   Used | Attended    → "Esta credencial ya registró asistencia."
   Expired            → credencial vencida
   escáner ∉ EventStaff del evento → no autorizado (cierra divergencia §20.6)
   fuera de ventana D-08           → fuera del horario del evento
4. Crear EventAttendance (registration, event, student, qr_token_validated,
   scanned_by_staff, scanned_at = servidor).
5. registration.qr_status = Used ; attendance_status = Attended.
6. Commit.  UNIQUE(event, student) es la última defensa ante concurrencia:
   si salta, se traduce al mensaje de duplicado, no a un 500.
```

> El token **no se descifra para autorizar**: se busca en la BD. La firma solo evita fabricar tokens plausibles; la autoridad es la fila (RNF-05).

### 6.7 `gbp`

| ID | Caso de uso | Actor | Precondiciones | Efectos | Evento |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CU-GB1 | Enviar trámite | `submit_gbp_reports` | Club `Active`; PAO indicado; `.pdf` validado | G1 + `roster_snapshot` (D-09) | `process.submitted` |
| CU-GB2 | Listar buzón | GBP | — | Trámites con club, PAO y estado | — |
| CU-GB3 | Tomar trámite | GBP | Estado `Submitted` | G2; fija `reviewed_by` | — |
| CU-GB4 | Aprobar | GBP | Estado `Under Review` | G3 | `process.approved` |
| CU-GB5 | Rechazar | GBP | Estado `Under Review`; feedback no vacío (**RN-5**) | G4 | `process.rejected` |
| CU-GB6 | Exportar | GBP | Formato `xlsx` o `pdf` únicamente (RNF-08) | Genera archivo desde el snapshot, no desde datos vivos | — |
| CU-GB7 | Catálogo global | GBP | — | Clubes con líder resuelto y conteo de activos | — |
| CU-GB8 | Histórico por PAO | GBP | — | Clubes, líderes y nóminas del período (RF-49) | — |

### 6.8 `notifications`

| ID | Caso de uso | Actor | Precondiciones | Efectos |
| :--- | :--- | :--- | :--- | :--- |
| CU-NO1 | Listar | Autenticado | Solo las propias | Orden descendente por fecha |
| CU-NO2 | Marcar leídas | Autenticado | Solo las propias | `read = True` |
| CU-NO3 | Emitir *(interno)* | Handler de evento | Idempotente por `(user, type, target)` | Crea `Notification` |

---

## 7. Invariantes: qué los defiende

### 7.1 Invariantes estructurales (defensa en BD)

| ID | Invariante | Mecanismo | Regla |
| :--- | :--- | :--- | :--- |
| I-01 | `Student.enrollment` único | `UNIQUE` | RF-05 |
| I-02 | `Student.email` único | `UNIQUE` | RF-01 |
| I-03 | `EventAttendance (event, student)` único | `UNIQUE` | **RN-6** |
| I-04 | `EventRegistration (event, student)` único | `UNIQUE` | Doble inscripción |
| I-05 | `EventRegistration.qr_token` único | `UNIQUE` | RNF-05 |
| I-06 | `Membership (student, club, pao)` único | `UNIQUE` | Una por club y período |
| I-07 | `Role (club, role_name)` único | `UNIQUE` | Nombre único por club |
| I-12 | `EventStaff (event, student)` único | `UNIQUE` | Asignación única |
| I-13 | `PaoPeriod.end_date > start_date` | `CHECK` | F-19 |
| I-14 | `Event.end_datetime >` inicio | `CHECK` | F-13 |
| I-15 | `Form.version` único por familia | `UNIQUE (club, form_type, event, version)` | D-03 |

### 7.2 Invariantes **condicionales** — el punto difícil

Tres invariantes son unicidades *parciales*: solo aplican cuando una condición se cumple. No son expresables como `UNIQUE` simple.

| ID | Invariante | Condición | Regla |
| :--- | :--- | :--- | :--- |
| **I-08** | Un solo `PaoPeriod` activo | `status = 'Active'` | RF-45 |
| **I-09** | Una sola `Membership` activa de liderazgo por estudiante | `status='Active' AND is_leadership` | **RN-1** |
| **I-10** | Una sola `MembershipApplication` `Pending` por `(student, club)` | `status = 'Pending'` | **RN-2** |

**Cómo se implementan según el motor:**

- **PostgreSQL** — soporta índices únicos parciales de forma nativa: `UniqueConstraint(fields=[...], condition=Q(...))`. Directo.
- **MySQL 8.x** — **no** soporta índices parciales ni `UNIQUE` con `WHERE`. Se resuelve con el patrón de **columna generada + índice único**, aprovechando que un índice único de MySQL admite múltiples `NULL`:

  | Invariante | Columna generada (STORED) | Índice |
  | :--- | :--- | :--- |
  | I-08 | `active_lock = CASE WHEN status='Active' THEN 1 END` | `UNIQUE(active_lock)` |
  | I-09 | `leadership_lock = CASE WHEN status='Active' AND is_leadership THEN student_id END` | `UNIQUE(leadership_lock)` |
  | I-10 | `pending_lock = CASE WHEN status='Pending' THEN CONCAT(student_id,'-',club_id) END` | `UNIQUE(pending_lock)` |

  Las filas que no cumplen la condición generan `NULL` y no compiten por el índice. Django expresa esto con `GeneratedField(db_persist=True)` + `UniqueConstraint`.
  **Restricción del motor:** una columna generada **no puede referenciar otras tablas** — por eso I-09 exige el snapshot `Membership.is_leadership` de D-05. Sin ese snapshot, RN-1 solo puede defenderse en la aplicación, y una condición de carrera puede producir dos liderazgos.

- **Ambos motores** — la defensa de BD se acompaña siempre de validación en el servicio, que produce el mensaje de negocio. El constraint existe para la concurrencia; el servicio, para el usuario.

### 7.3 Invariantes de aplicación (no expresables en BD)

| ID | Invariante | Dónde se aplica | Regla |
| :--- | :--- | :--- | :--- |
| I-11 | `role.club == membership.club` | `Membership.clean()` + servicio | RF-09 |
| I-16 | Feedback obligatorio al rechazar (solicitud y trámite) | `clean()` + serializer | **RN-5** |
| I-17 | Un formulario con respuestas no se edita | Servicio CU-FO2 (`409`) | RF-24 |
| I-18 | `manage_roles` solo en roles `is_leadership` | Serializer de `Role` | **RN-7** |
| I-19 | Un club `Pending Leader` no acepta escrituras | *Policy* transversal | RF-13 |
| I-20 | Staff ⊆ miembros activos del club del evento | Servicio CU-EV6 | RF-35 |
| I-21 | Solo staff del evento escanea, dentro de la ventana | Servicio CU-EV9 | RF-35, D-08 |
| I-22 | Trámite `Submitted` no editable por el club | Servicio | RF-41 |
| I-23 | Coherencia `Club.status` ↔ liderazgo | Servicios de liderazgo (C1–C5) | D-01 |
| I-24 | Respuestas válidas contra el esquema del formulario | CU-FO6 | RF-23 |
| I-25 | Formatos: solo `.pdf` (documentos) y `.xlsx`/`.pdf` (exportación), validando content-type | Validador de subida | RNF-08 |

> **Ninguna de estas se delega al cliente.** Todas las validaciones de MASTER §12 son de cliente y deben replicarse aquí; el frontend es no confiable por definición.

---

## 8. Modelo de autorización

### 8.1 Dos planos independientes

1. **Plano institucional** — `is_gbp_admin`. Booleano en `Student`. Otorga acceso al panel GBP y a las operaciones de auditoría. **No** otorga permisos dentro de un club: GBP audita y valida, no edita (MASTER §3.1).
2. **Plano de club** — `Membership(Active).role.permissions`. Diccionario por club. Es el **único** origen de los permisos operativos. Clave ausente = `False`.

No se usa el sistema `auth.Permission` de Django para el plano de club: aquel es global y estos permisos son **por club**.

### 8.2 Predicados de autorización

| Predicado | Definición |
| :--- | :--- |
| `IsGbpAdmin` | `user.is_gbp_admin` |
| `IsClubMember(club)` | Existe `Membership(user, club, status=Active)` |
| `HasClubPermission(club, perm)` | `IsClubMember(club)` **y** `role.permissions.get(perm) is True` **y** `club.status == Active` |
| `IsEventStaff(event)` | Existe `EventStaff(event, user)` **y** ahora ∈ ventana D-08 |
| `IsSelf(student)` | `user.id == student.id` |
| `CanSeeRoster(club)` | `IsClubMember(club)` **o** `IsGbpAdmin` |

> `HasClubPermission` incluye `club.status == Active` en su propia definición: así I-19 se cumple en **todas** las operaciones de club sin repetir la comprobación en cada vista.

### 8.3 Matriz operación → autorización

| Operación | Requiere |
| :--- | :--- |
| Alta de club, asignar/revocar líder, PAO, buzón, exportar, histórico | `IsGbpAdmin` |
| Editar club, documentos | `HasClubPermission(manage_club_info` / `manage_documents)` |
| Nómina, cambio de rol, baja, renovación, bandeja, aprobar/rechazar | `HasClubPermission(manage_members)` |
| Crear/editar roles | `HasClubPermission(manage_roles)` **+ RN-7** |
| Constructor de formularios | `HasClubPermission(manage_forms)` |
| CRUD de eventos, staff, bitácora | `HasClubPermission(manage_events)` |
| Enviar trámite a GBP | `HasClubPermission(submit_gbp_reports)` |
| Escanear QR | `IsEventStaff(event)` |
| Entrar al panel web del club | `HasClubPermission(access_web_panel)` |
| Ver nómina detallada | `CanSeeRoster(club)` |
| Postular, inscribirse, ver credencial | Autenticado + verificado |
| Editar perfil | `IsSelf` |

---

## 9. Eventos de dominio y notificaciones

Los eventos desacoplan `notifications` (y futuros consumidores: correo, auditoría, métricas) del resto del sistema. Se emiten **después** del commit, no dentro de la transacción: una notificación fallida no debe deshacer una aprobación.

| Evento | Emisor | Destinatario de la notificación | `type` |
| :--- | :--- | :--- | :--- |
| `application.submitted` | CU-AP1 | Miembros del club con `manage_members` | `application_pending` |
| `application.approved` | CU-AP4 | Estudiante postulante | `application_approved` |
| `application.rejected` | CU-AP5 | Estudiante postulante | `application_rejected` |
| `membership.revoked` | CU-CL10 / C5 | Estudiante afectado | `membership_revoked` |
| `membership.renewed` | CU-CL12 | Cada miembro renovado | `membership_renewed` |
| `membership.frozen` | Proceso M2 | Cada miembro congelado | `membership_frozen` |
| `club.leader_assigned` | C3 / C4 | Nuevo líder | `leader_assigned` |
| `club.leader_revoked` | C5 | Líder saliente | `leader_revoked` |
| `event.registered` | CU-EV7 | Estudiante inscrito | `event_registered` |
| `attendance.registered` | CU-EV9 | Estudiante asistente | `attendance_registered` |
| `process.submitted` | CU-GB1 | Administradores GBP | `gbp_review` |
| `process.approved` / `.rejected` | CU-GB4/5 | Líder del club | `gbp_resolution` |
| `student.verified` | CU-AC2 | *(sin notificación; dispara C3)* | — |

Cierra la divergencia §20.18 de MASTER: en Fase 1 ningún flujo crea notificaciones; aquí **todo cambio de estado relevante** emite una.

---

## 10. Procesos programados

Cuatro comandos idempotentes. Idempotente = ejecutarlo dos veces produce el mismo estado y **no** duplica notificaciones (por eso CU-NO3 deduplica por `(user, type, target)`).

| Comando | Frecuencia | Selección | Acción | Regla |
| :--- | :--- | :--- | :--- | :--- |
| `freeze_expired_memberships` | Diaria | `status=Active AND valid_until < hoy` | → `Frozen` (M2) | RF-20, RN-4 |
| `expire_stale_memberships` | Diaria | `status=Frozen`, PAO `Closed`, sin membresía del mismo `(student, club)` en PAO de `sequence` mayor | → `Expired` (M3) | RF-19 |
| `expire_qr_tokens` | Horaria | `qr_status=Active AND event.end_datetime < ahora` | → `Expired` (Q2) | RF-37 |
| `mark_no_shows` | Horaria | `attendance_status=Registered AND event.end_datetime < ahora` | → `NoShow` (Q3) | §5.4 |

**Reglas de diseño:**
- Cada comando acepta `--dry-run` y reporta cuántas filas tocaría. Sin esto no son auditables.
- El "ahora" se inyecta como parámetro, no se lee de `timezone.now()` dentro del bucle: hace las pruebas deterministas.
- Se procesan en lotes: la nómina completa de la institución al cierre de un PAO es la carga máxima previsible del sistema.
- `expire_qr_tokens` y `mark_no_shows` recorren el mismo conjunto de eventos finalizados: pueden compartir consulta, pero se mantienen separados porque los dos ejes de estado son independientes (§5.4).

---

## 11. Políticas de visibilidad

RN-3 y RNF-06 no son un filtro en la vista: son una **política de proyección**. La misma entidad se proyecta distinto según quién pregunta.

| Entidad | Anónimo/no miembro | Miembro del club | Líder (con permiso) | GBP |
| :--- | :--- | :--- | :--- | :--- |
| `Club` | Datos generales + **solo `members_count`** + documentos `is_public` | + nómina (nombre, carrera, rol) + todos los documentos | + correos, matrículas, vigencias | Todo + histórico |
| `Membership` | **No se expone** | Nombre, carrera, rol | + matrícula, correo, vigencia | Todo |
| `Student` | Nombre público mínimo | Nombre, carrera, facultad | + matrícula, correo, semestre | Todo |
| `Event` | Todos los eventos, incl. `MembersOnly` (RF-31) | + estado de registro | + métricas, inscritos, staff | Consulta |
| `ClubDocument` | Solo `is_public=True` | Todos los del club | Todos + gestión | Todos |
| `MembershipApplication` | Solo las propias | Solo las propias | Todas las del club | — |
| `GbpDocumentProcess` | — | — | Los del propio club | Todos |

**Prueba de aceptación obligatoria (MASTER §16.7):**
`GET /clubs/{id}/` ejecutado por un estudiante que **no** es miembro **nunca** debe contener un nombre o correo de miembro en el cuerpo de la respuesta. Esta es una prueba automatizada, no una revisión manual.

**Implementación:** dos serializers por entidad sensible, elegidos por `get_serializer_class()` a partir del predicado `CanSeeRoster`. Nunca por un `if` dentro de un `to_representation` — esa forma filtra datos por descuido cuando la entidad se anida en otra respuesta.

---

## 12. Cierre de divergencias y preguntas pendientes

### 12.1 Divergencias de MASTER §20

| # | Divergencia | Resolución en este documento |
| :-- | :--- | :--- |
| 1 | ¿3 o 4 roles por defecto? | **4.** CU-CL1 los crea siempre |
| 2 | `role_id` del Miembro mock | **10** (*Miembro*); 11 es *Encargado de Documentos* |
| 3 | Campos de `Club` | Rige §7.2 de MASTER, refinado por D-01 |
| 4 | `administrative_data` del evento | **D-07**: tabla 1:1 opcional |
| 5 | Asistencia sin `registration`/`qr_token_validated` | **D-06**: obligatorios |
| 6 | Staff no validado al escanear | **I-21 / CU-EV9**: obligatorio |
| 7 | `getVisibleEvents` ignora el estudiante | Correcto por diseño: CU-EV4 devuelve todo; CU-EV5 bloquea el registro |
| 8 | `members_count` y `stats` denormalizados | **P-5**: derivados |
| 9 | Documentos y staff embebidos | Tablas propias `ClubDocument` y `EventStaff` |
| 10–13 | Deuda de la pantalla Bitácora | Ver PPD-04 abajo; el resto es frontend |
| 14 | FastAPI → Django | Confirmado |
| 15 | Congelamiento y expiración inexistentes | **§10**: cuatro comandos |
| 16 | RN-1 sin validar | **I-09** + D-05 (snapshot) + CU-CL9/CL14 |
| 17 | RN-7 sin aplicar | **I-18** |
| 18 | Notificaciones de solo lectura | **§9**: eventos de dominio |

### 12.2 Preguntas pendientes de MASTER §21

| ID | Resolución |
| :--- | :--- |
| **PPD-01** *(facultades)* | Se implementa como **catálogo en BD** (app `catalogs`), no como enum de código: ampliar la lista oficial no debe requerir una migración |
| **PPD-02** *(cuentas GBP)* | **CU-AC7**: `management command`. Sin auto-registro para GBP; `is_gbp_admin` nunca se expone en el serializer de registro |
| **PPD-03** *(QR sin conexión)* | Fuera de alcance de Fase 2 (RNF-11 no exige offline). El diseño no lo impide: el token es opaco y validable después |
| **PPD-04** *(alcance de la Bitácora)* | **Bitácora = inscritos de un evento seleccionable** (CU-EV10), con selector y estado vacío. El log de acciones auditables (RF-52) es una preocupación distinta, cubierta por `resolved_by`/`scanned_by`/timestamps de D-04 |
| **PPD-05** *(quién marca `Under Review`)* | **GBP explícitamente** (CU-GB3 / G2), no al abrir el PDF. Motivo en §5.5 |

---

## 13. Estructura Django resultante

Traducción directa de todo lo anterior. Cada app repite el mismo esqueleto: **modelos → selectores → servicios → políticas → serializers → vistas**.

```
espolclub/
├── config/
│   ├── settings/{base,dev,prod}.py
│   ├── urls.py
│   └── celery.py
├── core/                          # sin modelos: contratos compartidos
│   ├── exceptions.py              # BusinessRuleViolation, StateTransitionError, PermissionDenied
│   ├── events.py                  # bus de eventos de dominio (§9)
│   ├── services.py                # base transaccional de comandos
│   └── validators.py              # dominio de correo, PDF/XLSX + content-type, URL
├── apps/
│   ├── accounts/                  # Student, verificación, JWT, rol derivado (D-11, D-12)
│   ├── academic/                  # PaoPeriod (I-08, D-14)
│   ├── catalogs/                  # facultades, áreas de interés (PPD-01)
│   ├── clubs/
│   │   ├── models.py              # Club, ClubDocument, Role, Membership
│   │   ├── selectors.py           # catálogo, nómina, detalle por privacidad
│   │   ├── services/
│   │   │   ├── clubs.py           # CU-CL1..CL5
│   │   │   ├── roles.py           # CU-CL6..CL8  (RN-7)
│   │   │   ├── memberships.py     # CU-CL9..CL12 (RN-1, RN-4)
│   │   │   └── leadership.py      # CU-CL13, CL14 (C1..C5, RN-1)
│   │   └── policies.py            # HasClubPermission, IsClubMember, CanSeeRoster
│   ├── dynamicforms/              # CU-FO1..FO6  ← CU-FO6 es servicio compartido
│   ├── applications/              # CU-AP1..AP5  (RN-2, RN-5)
│   ├── events/
│   │   ├── services/
│   │   │   ├── events.py          # CU-EV1..EV6
│   │   │   ├── registration.py    # CU-EV7, EV8 + emisión del token
│   │   │   └── attendance.py      # CU-EV9  (RN-6, transacción + bloqueo)
│   │   └── qr.py                  # firma y validación del token (RNF-05)
│   ├── gbp/                       # CU-GB1..GB8 + exportaciones
│   └── notifications/             # handlers de §9 (CU-NO1..NO3)
├── management/commands/           # los 4 procesos de §10
└── fixtures/                      # datos semilla de MASTER §17
```

**Contrato de cada capa:**

| Capa | Puede | No puede |
| :--- | :--- | :--- |
| `models.py` | Definir estructura, constraints, `clean()` de invariantes intra-agregado | Orquestar operaciones, enviar correos, emitir eventos |
| `selectors.py` | Leer y aplicar políticas de visibilidad | Mutar |
| `services/` | Mutar, validar reglas que cruzan agregados, abrir transacción, emitir eventos | Conocer HTTP, request o serializers |
| `policies.py` | Responder sí/no sobre un actor y un objeto | Mutar |
| `serializers.py` | Validar forma de entrada, proyectar salida | Contener reglas de negocio |
| `views.py` | Autenticar, deserializar, llamar servicio, serializar | Cualquier lógica de negocio |

---

## 14. Orden de construcción

Cada etapa termina en una verificación ejecutable. No se avanza sin ella.

| # | Etapa | Contenido | Verificación |
| :-- | :--- | :--- | :--- |
| 1 | **Cimientos** | `core`, `accounts`, `academic`, `catalogs` | El `Student` es `AUTH_USER_MODEL`; se crea un PAO y activar uno cierra los demás (I-08) |
| 2 | **Clubes** | `clubs` completo con I-06, I-07, I-09, D-01, D-05 | Dar de alta un club crea 4 roles; RN-1 rechaza el segundo liderazgo |
| 3 | **Fixtures** | Datos semilla de MASTER §17 | `loaddata` reproduce el estado de Fase 1; el club 4 queda `Pending Leader` |
| 4 | **Auth y roles derivados** | JWT, verificación, activación diferida (C3) | Los 4 usuarios semilla entran; `/auth/me/` devuelve el rol correcto |
| 5 | **Formularios** | `dynamicforms` con CU-FO6 y versionado D-03 | Editar un formulario con respuestas devuelve `409` y ofrece versionar |
| 6 | **Solicitudes** | `applications` con RN-2 y RN-5 | Kevin (`Rejected`) puede reaplicar; Lucía (`Pending`) no puede duplicar |
| 7 | **Eventos y QR** | `events` completo, CU-EV9 con transacción y bloqueo | Reescanear el token de la inscripción 7002 falla; un no-staff no puede escanear |
| 8 | **Lectura con privacidad** | Selectores y serializers de §11 | La prueba de aceptación de §11 pasa |
| 9 | **GBP** | `gbp` con G1..G4 y snapshot D-09 | Un trámite `Submitted` no admite edición del club |
| 10 | **Procesos y notificaciones** | Los 4 comandos + handlers de §9 | Ejecutados dos veces no duplican estados ni notificaciones |
| 11 | **Exportaciones** | `.xlsx` y `.pdf` desde el snapshot | GBP descarga la nómina del PAO cerrado y coincide con la evidencia |
| 12 | **Convergencia** | Reescribir `js/data-service.js` contra la API | **Ninguna pantalla del frontend cambia** |

> Etapas 1–3 son el cimiento: cualquier error de modelado allí se paga en migraciones dolorosas después. Etapa 7 concentra el riesgo técnico (concurrencia). Etapa 12 es la validación del diseño completo de Fase 1.

---

## 15. Motor de base de datos

`MASTER.md` §16.1 elige **PostgreSQL** por `JSONField` nativo. La decisión sigue siendo la recomendada, y este es el motivo concreto en términos de este documento:

| Necesidad | PostgreSQL | MySQL 8.x |
| :--- | :--- | :--- |
| I-08, I-09, I-10 (unicidad condicional) | Índice único parcial, nativo | Columna generada + `UNIQUE`, con la limitación de no poder cruzar tablas (§7.2) |
| Consulta sobre `permissions`, `fields`, `responses` | `JSONB` con operadores e índices GIN | `JSON` consultable, sin índice directo (requiere columna generada indexada) |
| `interest_areas` (filtro del catálogo, RF-46) | Arreglo o `JSONB` indexable | Requiere tabla puente o columna generada |
| Snapshots (`roster_snapshot`) | `JSONB` | `JSON`, suficiente |

**Si el proyecto debe correr sobre MySQL** (restricción del curso o del hosting), el diseño de este documento **funciona sin cambios estructurales**, con tres condiciones que ya están incorporadas:

1. `Membership.is_leadership` como snapshot (D-05) — indispensable, no opcional, para poder defender RN-1 en la BD.
2. Las tres unicidades condicionales implementadas con columnas generadas `STORED` + índice único (§7.2).
3. `interest_areas` promovido a tabla puente `ClubInterestArea` en vez de JSON, para que el filtro del catálogo (RF-46, la funcionalidad prioritaria del sistema según MASTER §1.3) sea indexable en vez de un escaneo completo.

Los tres son mejoras defendibles también en PostgreSQL; el punto 3 lo es especialmente, porque convierte la consulta más frecuente del sistema en una búsqueda por índice.

---

*Estructura lógica de negocio de ESPOLCLUB. Derivada de `MASTER.md`. Precede a `models.py`.*
