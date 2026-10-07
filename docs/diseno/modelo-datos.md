# Modelo de datos

Tablas de PostgreSQL 16 que implementa la B-02. La B-02 se cierra cuando los
modelos de SQLAlchemy coinciden con este diagrama; si cambian, se actualiza
este archivo en el mismo PR.

## Diagrama entidad-relación

```mermaid
erDiagram
  usuarios ||--o{ sesiones : "abre"
  usuarios ||--o{ progreso_lecciones : "avanza"
  usuarios ||--o{ intentos : "responde"
  usuarios ||--o{ labs : "corre"
  usuarios ||--o| graduaciones : "envía"
  usuarios |o--o{ graduaciones : "revisa"
  usuarios |o--o{ auditoria : "actúa"
  cursos ||--|{ modulos : "contiene"
  modulos |o--o{ modulos : "es prerrequisito de"
  modulos ||--|{ lecciones : "contiene"
  videos |o--o{ lecciones : "se muestra en"
  lecciones ||--o| quizzes : "cierra con"
  quizzes ||--|{ preguntas : "tiene"
  preguntas ||--|{ opciones : "tiene"
  quizzes ||--o{ intentos : "recibe"
  lecciones ||--o{ progreso_lecciones : "registra"

  usuarios {
    bigint id PK
    text username UK "igual al del clúster"
    text nombre
    text correo
    text cluster "apolo2 | apolo3"
    text rol "estudiante | instructor | admin"
    text idioma "es | en"
    text clave_hash "argon2id"
    bool debe_cambiar_clave
    int intentos_fallidos
    timestamptz bloqueado_hasta
    bool activo "false = dado de baja"
    timestamptz creado_en
    timestamptz baja_en
    timestamptz ultimo_ingreso
  }

  sesiones {
    bigint id PK
    bigint usuario_id FK
    text refresh_hash UK "sha256 del refresh"
    timestamptz creada_en
    timestamptz expira_en
    timestamptz ultimo_uso_en
    timestamptz revocada_en
  }

  cursos {
    bigint id PK
    text slug UK
    text titulo_es
    text titulo_en
    text descripcion_es
    text descripcion_en
    int orden
    bool publicado
  }

  modulos {
    bigint id PK
    bigint curso_id FK
    text slug "único por curso"
    int numero "0 a 9"
    text titulo_es
    text titulo_en
    text resumen_es
    text resumen_en
    int duracion_min
    bigint prerrequisito_id FK "módulo anterior"
  }

  lecciones {
    bigint id PK
    bigint modulo_id FK
    text slug "único por módulo"
    int orden
    text titulo_es
    text titulo_en
    text contenido_es "Markdown"
    text contenido_en "Markdown, puede faltar"
    int duracion_min
    bigint video_id FK "opcional"
    jsonb escenario "terminal quemada, opcional"
    text lab "modulos | memoria | nucleos | paralelo, opcional"
    bool publicada "false si salió del repo"
    timestamptz actualizado_en
  }

  videos {
    bigint id PK
    text clave UK "m05-trabajos"
    text archivo "ruta relativa en media, null si no se ha subido"
    int duracion_seg
    bigint tamano_bytes
    text vtt_es
    text vtt_en
    bigint subido_por FK
    timestamptz subido_en
  }

  quizzes {
    bigint id PK
    bigint leccion_id FK "único"
    text clave UK
    numeric umbral "0.80"
    bool es_final
  }

  preguntas {
    bigint id PK
    bigint quiz_id FK
    text clave UK
    int orden
    text enunciado_es
    text enunciado_en
    text explicacion_es
    text explicacion_en
    bool multiple
  }

  opciones {
    bigint id PK
    bigint pregunta_id FK
    int orden
    text texto_es
    text texto_en
    bool correcta "nunca sale al navegador antes de responder"
  }

  intentos {
    bigint id PK
    bigint usuario_id FK
    bigint quiz_id FK
    numeric puntaje "0 a 100"
    bool aprobado
    jsonb respuestas
    timestamptz creado_en
  }

  progreso_lecciones {
    bigint usuario_id PK, FK
    bigint leccion_id PK, FK
    int video_posicion_seg "para reanudar"
    int video_max_seg
    bool video_completo
    bool terminal_completa
    bool quiz_aprobado
    timestamptz completada_en
    timestamptz actualizado_en
  }

  labs {
    bigint usuario_id PK, FK
    text lab PK "modulos | memoria | nucleos | paralelo"
    text estado "intentado | aprobado"
    text jobid
    text detalle "mensaje del verificador"
    timestamptz fecha "fin del trabajo en Slurm"
    timestamptz sincronizado_en
  }

  sincronizaciones {
    bigint id PK
    timestamptz recibida_en
    int registros
    int aceptados
    text origen "vm-practica"
  }

  graduaciones {
    bigint usuario_id PK, FK
    text cluster "apolo2 | apolo3"
    text jobid
    text salida_verificador
    text estado "enviada | aprobada | rechazada"
    timestamptz enviada_en
    bigint revisada_por FK
    timestamptz revisada_en
    text comentario
    timestamptz qos_aplicada_en
    bigint qos_aplicada_por FK
  }

  auditoria {
    bigint id PK
    bigint actor_id FK "null si fue un servicio"
    text actor_servicio "vm-practica, null si fue una persona"
    text accion
    text objetivo "username u objeto afectado"
    jsonb detalle
    inet ip
    timestamptz creado_en
  }
```

`sincronizaciones` no tiene relaciones: es el registro de cada envío de la VM
de práctica y de ahí sale la «última sincronización» de Mi progreso.

## Tablas

### Personas y sesiones

**usuarios.** Una fila por persona. `username` es el mismo de su cuenta en el
clúster y también el de la VM de práctica; por eso es único y no se cambia.
`cluster` decide el perfil de la VM y la pestaña que se abre por defecto en las
lecciones. Una baja no borra la fila: pone `activo = false` y `baja_en`, para
conservar el progreso y la auditoría.

- Bloqueo: `intentos_fallidos` llega a 5 → `bloqueado_hasta = ahora + 15 min`
  y se reinicia a 0 al entrar bien (B-03).
- `debe_cambiar_clave` empieza en `true` y la API solo deja usar `/auth/*` y
  `GET /me` hasta que se cambie.

**sesiones.** Una fila por refresh token emitido. Se guarda solo el hash, nunca
el token. Sirve para cerrar sesión de verdad (logout, cambio de clave, baja o
reinicio de clave revocan todas las sesiones del usuario). Se borran las
vencidas con una tarea diaria.

### Contenido

El contenido vive en `content/` del repo y lo carga `training import-content`
(B-04). El importador busca por `slug` o `clave`, así que importar dos veces no
duplica filas y el progreso de los usuarios no se pierde.

**cursos, modulos, lecciones.** Hoy hay un curso con diez módulos (0 a 9).
`modulos.prerrequisito_id` apunta al módulo anterior; el siguiente se abre
cuando todas las lecciones del anterior están completas.

Una lección no tiene un `tipo` fijo: puede traer cualquier combinación de
video, lectura, terminal quemada, laboratorio y quiz, igual que la plantilla de
la C-01. Se completa cuando cumple todo lo que trae:

| Si la lección trae… | …se cumple cuando                                       |
| ------------------- | ------------------------------------------------------- |
| video               | `video_max_seg` ≥ 90 % de la duración                   |
| terminal quemada    | el escenario llega al último paso (`terminal_completa`) |
| quiz                | un intento con 80 % o más (`quiz_aprobado`)             |
| solo lectura o lab  | el usuario pulsa «Marcar como completada»               |

El laboratorio **no** bloquea la lección ni el módulo siguiente: su resultado
llega desde la VM cada 5 minutos y cuenta para aprobar el curso, no para
navegar.

**videos.** Una fila por video, identificada por `clave` (`m01-conexion`,
`m04-modulos`, `m05-trabajos`, `m06-paralelismo`, `m07-ondemand`). El front
matter de la lección dice `video: m05-trabajos`; el importador crea la fila sin
archivo y el instructor sube el MP4 y los VTT desde el panel con esa clave.
Mientras no haya archivo, la lección muestra «Video pendiente». Las rutas son
relativas a `/srv/apolo-training/media`.

**quizzes, preguntas, opciones.** Un quiz pertenece a una lección (el quiz del
módulo va en su última lección; el quiz final de 15 preguntas tiene
`es_final = true`). Los textos van en los dos idiomas; si falta el inglés, la
API devuelve el español con `fallback = true`. La columna `opciones.correcta`
nunca se envía al navegador antes de que el usuario responda (B-06).

### Progreso

**intentos.** Cada envío de un quiz, con las respuestas en `jsonb`
(`{"<pregunta_id>": [<opcion_id>, ...]}`) y el puntaje calculado en el servidor.
Intentos ilimitados; cuenta el mejor.

**progreso_lecciones.** Una fila por usuario y lección, creada en el primer
reporte. `video_posicion_seg` es donde se reanuda; `video_max_seg` es lo más
lejos que llegó. `completada_en` se llena una sola vez.

**labs.** El último estado conocido de cada laboratorio por usuario, tal como lo
envía la VM de práctica (V-05). Regla del upsert: un `aprobado` nunca se
reemplaza por un `intentado` posterior. Si no hay fila, la pantalla muestra
«sin intentar».

**sincronizaciones.** Un registro por cada `POST /api/internal/labs`, aunque no
traiga cambios. Si el último tiene más de 15 minutos, Mi progreso avisa (F-07).

**graduaciones.** Una por usuario. El estudiante envía el JobID de su sesión de
OnDemand en el clúster real y la salida de `apolo-training verificar ondemand`;
un instructor la aprueba o la rechaza con un comentario. Cuando un admin aplica
la QOS normal en el clúster real, marca `qos_aplicada_en`.

### Auditoría

**auditoria.** Solo agrega filas. Acciones previstas: `login_ok`,
`login_fallido`, `cuenta_bloqueada`, `cambio_clave`, `alta`, `baja`,
`reinicio_clave`, `cambio_rol`, `video_subido`, `graduacion_enviada`,
`graduacion_revisada`, `qos_aplicada`, `sincronizacion_rechazada`. Nunca guarda
contraseñas, tokens ni el contenido de las terminales.

## Cuándo se aprueba el curso

Un usuario aparece en «aprobados pendientes de QOS» cuando cumple las tres
condiciones:

1. Todas las lecciones de los diez módulos completas (incluye el quiz final con
   80 % o más).
2. Los cuatro laboratorios en `aprobado`.
3. La graduación en `aprobada`.

Es una consulta, no una columna: no hay un estado «aprobado» guardado que se
pueda desincronizar.

## Índices y restricciones

| Tabla                | Índice o restricción                                        |
| -------------------- | ----------------------------------------------------------- |
| usuarios             | `username` único; índice en `(cluster, activo)`             |
| sesiones             | `refresh_hash` único; índice en `usuario_id`                |
| modulos              | único `(curso_id, slug)`; único `(curso_id, numero)`        |
| lecciones            | único `(modulo_id, slug)`; único `(modulo_id, orden)`       |
| quizzes              | `leccion_id` único                                          |
| intentos             | índice en `(usuario_id, quiz_id)`                           |
| progreso_lecciones   | PK `(usuario_id, leccion_id)`; índice en `leccion_id`       |
| labs                 | PK `(usuario_id, lab)`; `CHECK` de `lab` y `estado`         |
| graduaciones         | PK `usuario_id`; índice en `estado`                         |
| auditoria            | índices en `creado_en` y `actor_id`                         |
| todas las de estados | `CHECK` con los valores permitidos (en vez de tipos `ENUM`) |

Se usan `CHECK` en vez de `ENUM` de PostgreSQL porque agregar un valor a un
`ENUM` complica las migraciones de Alembic.

## Diferencias con la B-02 del plan

Para revisar en este PR; si se aprueban, se actualiza la tarjeta de la B-02.

- **`lecciones.tipo` pasa a componentes opcionales** (`video_id`, `escenario`,
  `lab` y el quiz asociado), porque la plantilla de la C-01 pone video, lectura,
  terminal y quiz en la misma lección.
- **Tablas nuevas:** `sesiones` (la B-03 necesita revocar refresh tokens),
  `quizzes` (agrupa las preguntas y da el `{id}` de `/api/quizzes/{id}`) y
  `sincronizaciones` (la F-07 necesita la hora de la última sincronización).
- **`videos` se identifica por `clave`**, para que el contenido del repo y la
  subida desde el panel se encuentren sin depender de ids de la base.
- Nombres en plural (`progreso_lecciones`, `graduaciones`) para que todas las
  tablas sigan la misma regla.
