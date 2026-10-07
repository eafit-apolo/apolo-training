# Diseño de la plataforma (A-11)

Pantallas, datos y API acordados antes de programar, para que el frontend
(F-01 en adelante) y el backend (B-01 en adelante) avancen en paralelo sin
rehacer.

| Archivo                                      | Qué tiene                                                                                                      |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| [pantallas.md](pantallas.md)                 | Los seis wireframes, qué muestra cada parte y qué rutas de la API usa                                          |
| [modelo-datos.md](modelo-datos.md)           | Diagrama entidad-relación de las tablas de la B-02, reglas e índices                                           |
| [flujos.md](flujos.md)                       | Alta de cuentas, sesión, terminal real, sincronización, graduación, video y carga del contenido                |
| [`api/openapi.yaml`](../../api/openapi.yaml) | Contrato OpenAPI 3.1 v0: 36 operaciones de auth, contenido, medios, progreso, quizzes, panel, admin e internal |

## Decisiones principales

- **Las cuentas se crean y se borran solo con `apolo-training-admin` en la VM
  de práctica**, que a su vez llama a la API. Así no puede quedar un usuario en
  la plataforma sin cuenta en la VM, ni al revés.
- **Hay dos contraseñas** (plataforma y VM) que empiezan iguales y se cambian
  por separado. La plataforma no guarda ni ve la contraseña de la VM: el usuario
  la escribe en la terminal real.
- **Una lección puede traer video, lectura, terminal quemada, laboratorio y
  quiz** a la vez, como la plantilla de la C-01; se completa cuando cumple lo
  que trae.
- **Los laboratorios no bloquean la navegación**, solo la aprobación del curso:
  su resultado llega cada 5 minutos desde la VM.
- **La graduación la trae el usuario** (JobID y salida del verificador de su
  clúster real) y la revisa un instructor, porque los clústeres reales no
  pueden escribir en la plataforma.
- **La API responde errores con un `codigo` estable** y la app arma el mensaje
  en el idioma elegido.
- **El panel de instructor y la administración de usuarios están separados**:
  dos entradas del menú, dos grupos de rutas (`/api/panel` para instructor y
  admin, `/api/admin` solo para admin) y dos pantallas.
- **El gateway de terminal valida la sesión con `GET /api/me`**, reenviando la
  cookie del usuario, y solo conecta a la VM de práctica con el usuario de la
  sesión.

## Roles

| Puede…                                             | Estudiante | Instructor | Admin |
| -------------------------------------------------- | :--------: | :--------: | :---: |
| Tomar el curso y ver su progreso                   |     sí     |     sí     |  sí   |
| Abrir lecciones de módulos bloqueados              |     no     |     sí     |  sí   |
| **Panel de instructor** (`/api/panel`)             |            |            |       |
| Ver el resumen y exportar el CSV de progreso       |     no     |     sí     |  sí   |
| Subir videos y subtítulos                          |     no     |     sí     |  sí   |
| Revisar graduaciones                               |     no     |     sí     |  sí   |
| **Administración** (`/api/admin`)                  |            |            |       |
| Ver usuarios y reiniciar la clave de la plataforma |     no     |     no     |  sí   |
| Cambiar roles                                      |     no     |     no     |  sí   |
| Ver aprobados y marcar «QOS aplicada»              |     no     |     no     |  sí   |
| Crear o dar de baja cuentas                        |     no     |     no     |  no¹  |

¹ Se hace con `apolo-training-admin` como root en la VM de práctica.

Cada operación de `api/openapi.yaml` declara sus roles en `x-roles`; es la base
de la matriz que pide la B-09.

## Para revisar en el PR

Byron, estas son las decisiones que más te afectan. Marca o comenta cada una:

- [ ] **Altas y bajas solo por CLI** (afecta V-04 y F-08): el panel muestra la
      orden en vez de crear la cuenta.
- [ ] **Gateway con `GET /api/me`** (afecta T-05): sin compartir la llave de
      los JWT. El protocolo de mensajes del WebSocket está en
      [flujos.md](flujos.md#3-terminal-real).
- [ ] **Formato del reporte de laboratorios** (afecta V-05): reporte completo
      cada 5 minutos, `estado` `intentado` o `aprobado`, y un `aprobado` no
      retrocede. Ver [flujos.md](flujos.md#4-sincronización-de-laboratorios).
- [ ] **Graduación enviada por el usuario** desde Mi progreso (afecta V-07 y
      el módulo 7).
- [ ] **Un perfil por usuario:** si alguien tiene cuenta en Apolo II y en
      Apolo III, en el curso elige uno. ¿Está bien?
- [ ] **Panel y administración separados:** un instructor no ve usuarios ni
      reinicia claves; eso queda para los admins.

## Cambios que este diseño propone al plan

Se aplican a las tarjetas cuando se apruebe este PR.

| Tarea      | Cambio                                                                                                                        |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------- |
| B-02       | `lecciones.tipo` pasa a componentes opcionales; tablas nuevas `sesiones`, `quizzes` y `sincronizaciones`                      |
| B-05       | La subida es `PUT /api/panel/videos/{clave}` (antes `POST /api/admin/videos`)                                                 |
| B-07, V-07 | Ruta nueva `POST /api/me/graduacion`; la revisión es `POST /api/panel/graduaciones/{username}/revision`                       |
| B-08, F-08 | Panel de instructor (`/api/panel`) y administración de usuarios (`/api/admin`, solo admin) separados                          |
| B-08, F-08 | El alta desde el panel se reemplaza por la orden de `apolo-training-admin`; el token de servicio usa `/api/internal/usuarios` |
| T-05       | La sesión se valida con `GET /api/me`; protocolo de mensajes definido                                                         |
| V-05       | Formato del reporte definido en `ReporteLabs`                                                                                 |

## Cómo revisarlo

- GitHub muestra los SVG y los diagramas Mermaid directamente en los `.md`.
- El contrato se abre en <https://editor.swagger.io> (File → Import file). Para
  validarlo en local: `npx @redocly/cli lint api/openapi.yaml`.

## Fuera de la v0

Recuperar la contraseña por correo, alta masiva por CSV, editor de lecciones en
la plataforma y texto de las lecciones en inglés. La API y el modelo ya dejan
espacio para todo eso.
