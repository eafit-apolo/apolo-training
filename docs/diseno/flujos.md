# Flujos

Cómo se mueven los datos entre el navegador, la plataforma (VM 117) y la VM de
práctica (VM 116). Las rutas de la API están en
[`api/openapi.yaml`](../../api/openapi.yaml); aquí va el orden de los pasos y lo
que OpenAPI no describe (el WebSocket de la terminal y el reporte de
laboratorios).

Nombres usados en los diagramas: **plataforma** es la VM 117 (nginx, api,
terminal y db en Docker Compose) y **VM de práctica** es la 116. Las IPs no se
escriben aquí porque el repo será público; están en el inventario cifrado de
Ansible.

## 1. Alta de una cuenta

Una sola orden crea al usuario en los dos lados. Se corre como root en la VM
de práctica porque ahí hay que crear la cuenta Unix y la asociación de Slurm;
la plataforma no tiene acceso de root a esa VM, y es mejor que no lo tenga.

```mermaid
sequenceDiagram
  actor A as Admin (root en la VM de práctica)
  participant C as apolo-training-admin
  participant V as VM de práctica
  participant API as API (plataforma)
  participant DB as PostgreSQL

  A->>C: alta ana --cluster apolo3 --correo ana@…
  C->>C: genera la clave temporal
  C->>V: useradd -g apolo3, chpasswd, chage -d 0
  C->>V: sacctmgr add user ana account=curso-apolo3 qos=curso
  C->>V: /etc/apolo-training/usuarios/ana = apolo3 y copia el laboratorio
  C->>API: POST /api/internal/usuarios (token de servicio)
  API->>DB: INSERT usuarios (argon2, debe_cambiar_clave)
  alt la API responde 201
    API-->>C: 201 Created
    C-->>A: clave temporal (una sola vez) y texto para el usuario
  else la API falla o no responde
    API-->>C: error
    C->>V: revierte: sacctmgr delete user, userdel -r, borra el perfil
    C-->>A: error, sin cuentas a medias
  end
```

- La **baja** sigue el mismo camino: `apolo-training-admin baja ana` bloquea la
  cuenta Unix, quita la asociación de Slurm y llama a
  `PATCH /api/internal/usuarios/ana` con `{"activo": false}`, que revoca sus
  sesiones. El home se archiva a los 30 días (V-04).
- Desde el panel web **no** se crean ni se borran cuentas: el botón «Nuevo
  usuario» muestra la orden para copiar. Si se crearan desde la web, quedaría
  un usuario en la plataforma sin cuenta en la VM y la terminal real fallaría.
- **Son dos contraseñas** que empiezan iguales: la de la plataforma y la de la
  VM. Cada una se cambia en su primer ingreso y desde ahí son independientes.
  El módulo 1 lo explica, y el reinicio de clave del panel solo cambia la de la
  plataforma (la de la VM se reinicia con `apolo-training-admin`).

## 2. Inicio de sesión y primer ingreso

```mermaid
sequenceDiagram
  actor U as Usuario
  participant W as App web
  participant API as API
  participant DB as PostgreSQL

  U->>W: usuario y contraseña temporal
  W->>API: POST /api/auth/login
  API->>DB: argon2, intentos_fallidos, bloqueado_hasta
  API-->>W: 200 + cookies at (15 min), rt (7 días), csrf
  Note over W: debe_cambiar_clave = true → la guardia lleva a /cambiar-clave
  U->>W: contraseña nueva (8 caracteres o más)
  W->>API: POST /api/auth/cambiar-clave + X-CSRF-Token
  API->>DB: hash nuevo, debe_cambiar_clave = false, revoca las demás sesiones
  API-->>W: 204
  W->>API: GET /api/me
  API-->>W: perfil (cluster, rol, idioma)
  Note over W,API: si una llamada da 401, el interceptor llama a POST /api/auth/refresh y la repite una vez
```

- **Cookies.** `at` (token de acceso, 15 min) y `rt` (refresh, 7 días, solo en
  `/api/auth`) son `HttpOnly`, `Secure` y `SameSite=Strict`. `csrf` es legible
  por la app y se devuelve en la cabecera `X-CSRF-Token` en todo lo que no sea
  `GET` (doble envío ligado a la sesión, B-03: es un HMAC del id de la sesión,
  así que una cookie `csrf` plantada por otro sitio no sirve).
- **Renovación.** Cada `POST /api/auth/refresh` rota `rt` y cuenta los 7 días
  otra vez. Un `rt` ya rotado que llega en los 30 s siguientes (otra pestaña)
  no cambia nada; si llega después, se cierran todas las sesiones del usuario.
- **Bloqueo.** Al quinto intento fallido, 15 minutos de bloqueo y el contador
  vuelve a 0. Un usuario inexistente recibe lo mismo que una clave errada.
- **Errores con código.** La API responde `{"detail": "...", "codigo": "..."}` y
  la app traduce el `codigo` con Transloco (`clave_incorrecta`,
  `cuenta_bloqueada`, `debe_cambiar_clave`…). Así los mensajes salen en el
  idioma de la interfaz sin que la API sepa de idiomas.
- Mientras `debe_cambiar_clave` sea `true`, todo salvo `/api/auth/*`,
  `GET /api/me` y `PATCH /api/me` responde 403 con `codigo = debe_cambiar_clave`.
- **En la app (F-03).** Al arrancar, si no hay cookie `csrf` no hay sesión y no
  se llama a la API; si la hay, `GET /api/me` trae el perfil y su idioma. Las
  guardias llevan a `/ingresar?volver=…` sin sesión, a `/cambiar-clave` con la
  clave temporal y a `/cursos` a quien abre Panel o Administración sin su rol.
  El interceptor renueva una sola vez aunque fallen varias peticiones a la vez;
  si la renovación falla, lleva a `/ingresar` con «Tu sesión terminó».
- **Olvidé mi contraseña:** en la v0 no hay correo saliente, así que la pantalla
  indica escribir a soporte y un instructor la reinicia desde el panel.

## 3. Terminal real

El gateway (contenedor `terminal`, T-05) solo sabe abrir SSH hacia la VM de
práctica, con el usuario de la sesión. El navegador no puede elegir host ni
usuario.

```mermaid
sequenceDiagram
  actor U as Usuario
  participant W as App web (xterm.js)
  participant N as nginx
  participant G as Gateway de terminal
  participant API as API
  participant V as VM de práctica (sshd)

  U->>W: Abrir terminal real
  W->>N: GET /ws/terminal (Upgrade, cookie at, Origin)
  N->>G: proxy del WebSocket
  G->>G: Origin igual al de la plataforma, si no 403
  G->>API: GET /api/me reenviando la cookie
  API-->>G: username, cluster, activo
  G->>G: si ya hay una sesión de ese usuario, la cierra
  G->>V: SSH al puerto 22 como el username de la sesión
  V-->>G: keyboard-interactive: Password
  G-->>W: el prompt de contraseña aparece en la terminal
  U->>W: escribe la contraseña de la VM
  W->>G: teclas (el gateway no las guarda ni las registra)
  G->>V: PTY con el tamaño de la ventana
  loop sesión
    W->>G: entrada y cambios de tamaño
    G-->>W: salida de la terminal
  end
  Note over G: cierra a los 15 min sin actividad o a las 2 h
  G->>G: registra inicio y fin de sesión, nunca el contenido
```

**Validar la sesión con `GET /api/me`** (propuesta para la T-05): el gateway no
necesita la llave de los JWT ni una ruta nueva; le pregunta a la API con la
misma cookie del usuario. Como las cookies son `SameSite=Strict` y el gateway
valida el `Origin`, otro sitio no puede abrir el WebSocket a nombre del usuario.
Si el token de acceso venció, la app hace `refresh` antes de conectar.

**Mensajes del WebSocket** (contrato entre T-05 y T-06):

| Dirección           | Marco   | Contenido                                                          |
| ------------------- | ------- | ------------------------------------------------------------------ |
| navegador → gateway | texto   | `{"tipo": "entrada", "datos": "ls -l\r"}`                          |
| navegador → gateway | texto   | `{"tipo": "tamano", "columnas": 120, "filas": 32}`                 |
| gateway → navegador | binario | bytes de salida de la terminal, tal cual                           |
| gateway → navegador | texto   | `{"tipo": "estado", "estado": "conectado"}`                        |
| gateway → navegador | texto   | `{"tipo": "estado", "estado": "cerrado", "motivo": "inactividad"}` |

Motivos de cierre: `inactividad`, `tiempo_maximo`, `otra_sesion`,
`ssh_rechazado`, `sesion_invalida`, `error`. La app los traduce y ofrece
reconectar.

Lo que decidió la implementación (T-05, ver [`terminal/`](../../terminal/README.md)):

- Una URL con parámetros (`/ws/terminal?host=…`) se rechaza con 403, igual que
  un `Origin` ajeno.
- `debe_cambiar_clave` cierra con `sesion_invalida`: primero se cambia la clave
  de la plataforma.
- Mientras sshd pide la contraseña, el gateway hace de editor de línea (Enter y
  Retroceso, sin eco). Con la PTY abierta, `entrada` va tal cual a la VM.
- `tamano` puede llegar antes de la PTY; si no llega, se abre con 80×24.
- Cuando el usuario sale del shell (`exit`), llega `estado: cerrado` sin
  `motivo`.
- La inactividad cuenta solo lo que el usuario escribe: un comando largo sin
  teclear nada también se cierra a los 15 minutos.
- La sesión de la plataforma se valida solo al conectar.

## 4. Sincronización de laboratorios

```mermaid
sequenceDiagram
  participant T as Timer (cada 5 min)
  participant C as apolo-training-admin reporte
  participant S as Slurm (sacct)
  participant N as nginx
  participant API as API
  participant DB as PostgreSQL

  T->>C: reporte --json
  C->>S: sacct -a de las cuentas curso-*
  C->>C: verificador: estado de cada laboratorio por usuario
  C->>N: POST /api/internal/labs (Bearer)
  N->>N: solo acepta la IP de la VM de práctica
  N->>API: proxy con X-Real-IP
  API->>API: valida token e IP otra vez
  API->>DB: upsert labs (un aprobado no retrocede)
  API->>DB: INSERT sincronizaciones
  API-->>C: 200 {aceptados, ignorados}
  Note over C: si la plataforma no responde, lo registra en el journal y el siguiente envío pone todo al día
```

**Formato del reporte** (lo produce la V-05 y lo recibe la B-07):

```json
{
  "generado_en": "2026-11-26T10:05:00-05:00",
  "registros": [
    {
      "usuario": "ana",
      "lab": "memoria",
      "estado": "aprobado",
      "jobid": "1042",
      "fecha": "2026-11-26T09:58:12-05:00",
      "detalle": "Terminó con --mem=4G después de OUT_OF_MEMORY con 1G"
    }
  ]
}
```

- `lab`: `modulos`, `memoria`, `nucleos` o `paralelo`. `estado`: `intentado` o
  `aprobado`.
- El reporte es **completo**, no incremental: trae el mejor estado de cada
  laboratorio de cada usuario. Así, si un envío se pierde, el siguiente lo
  corrige, y enviar el mismo reporte dos veces no cambia nada.
- Un usuario que no existe en la plataforma se devuelve en `ignorados` con el
  motivo; no rompe el resto del envío.

## 5. Graduación y QOS

La graduación ocurre en el clúster real del usuario, que no puede enviar nada a
la plataforma. Por eso el usuario trae el resultado a mano y un instructor lo
revisa.

```mermaid
sequenceDiagram
  actor U as Usuario
  participant R as Su clúster real (Apolo II o III)
  participant W as App web
  participant API as API
  actor I as Instructor
  actor A as Admin del clúster

  U->>R: abre y cierra una sesión de OnDemand
  U->>R: module load apolo-training y apolo-training verificar ondemand JOBID
  R-->>U: [APROBADO]
  U->>W: Mi progreso: JobID y salida del verificador
  W->>API: POST /api/me/graduacion
  I->>W: Panel: graduaciones por revisar
  I->>R: (opcional) sacct -j JOBID en ese clúster
  I->>W: Aprobar o rechazar con comentario
  W->>API: POST /api/panel/graduaciones/ana/revision
  Note over API: con módulos, laboratorios y graduación completos, aparece en aprobados pendientes
  A->>W: Administración: aprobados pendientes de QOS
  A->>R: sacctmgr modify user ana set qos=(QOS normal)
  A->>W: Marcar QOS aplicada
  W->>API: POST /api/admin/aprobados-pendientes/ana/qos-aplicada
```

## 6. Video y progreso

```mermaid
sequenceDiagram
  participant W as App web
  participant N as nginx
  participant API as API
  participant DB as PostgreSQL

  W->>N: GET /api/cursos/induccion/lecciones/m05/trabajos?lang=en
  N->>API: proxy
  API-->>W: lección con video (id, url, duración, subtítulos es y en)
  W->>N: GET /api/media/7 (con Range)
  N->>API: proxy
  API->>API: valida la sesión (cookie at)
  API-->>N: X-Accel-Redirect /media-interno/m05/m05-trabajos-20261105T140312-a1b2.mp4
  N-->>W: 206 con el fragmento pedido
  loop cada 15 s mientras se reproduce
    W->>API: POST /api/progreso/video {leccion_id, segundo}
    API->>DB: video_posicion_seg, video_max_seg
  end
  API->>DB: si video_max_seg ≥ 90 % y lo demás está cumplido, completada_en
```

- Los subtítulos en inglés se activan solos si la interfaz está en inglés (F-05)
  y se pueden apagar. Se piden igual: `GET /api/media/7/subtitulos/en`.
- El reporte cada 15 s pasa por el interceptor, así que también mantiene viva la
  cookie de acceso mientras el video corre. Tras una pausa de más de 15 minutos,
  la siguiente petición del video da 401: el reproductor renueva la sesión y
  vuelve al segundo donde iba (F-05).
- `/media-interno/` es una `location` `internal` de nginx (W-05): desde afuera
  da 404, así que nadie baja un video sin pasar por la API. En desarrollo no
  hay nginx y la API manda el archivo ella misma (`API_MEDIA_ENTREGA=api`).
- **Subida (B-05):** un instructor o admin manda el MP4 como cuerpo de
  `PUT /api/panel/videos/{clave}` (la clave sale del front matter). La API lo
  escribe mientras llega en `media/.subiendo/`, lee el formato y la duración
  con PyAV (415 si no es MP4 con H.264 y AAC), lo mueve a la carpeta del
  módulo con un nombre nuevo, actualiza `videos` y borra el archivo anterior.
  Los VTT van igual por `PUT /api/panel/videos/{clave}/subtitulos/{idioma}`.
  Con un video subido, su lección se completa al verlo (B-06).

## 7. Carga del contenido

`python -m app.importar` (B-04) lee `content/es` y `content/en`, valida cada
archivo con los esquemas de `content/schema/` y las reglas de
`content/README.md`, y hace upsert por `slug` y `clave` en una sola
transacción: si algo no cumple, no carga nada. Se corre después de
`alembic upgrade head`: en desarrollo lo hace el servicio `migrar`; en la 117,
el despliegue (W-06). Nunca borra progreso; una lección que desaparece del repo
queda despublicada, no borrada. Con `--revisar` solo valida, sin la base (job
`content` del CI).
