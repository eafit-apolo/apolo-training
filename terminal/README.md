# terminal

Gateway WebSocket ↔ SSH (T-05): abre desde el navegador una terminal real en la
VM de práctica, con la cuenta del usuario de la plataforma. El flujo y los
mensajes están en [`docs/diseno/flujos.md`](../docs/diseno/flujos.md), «3.
Terminal real».

## Cómo funciona

1. El navegador abre `wss://…/ws/terminal`. Si el `Origin` no es el de la
   plataforma, o la URL trae parámetros, se rechaza con 403 antes de aceptar.
2. El gateway reenvía la cookie `at` a `GET /api/me`. Sin sesión, con la cuenta
   de baja o con la clave temporal sin cambiar: `sesion_invalida`. No conoce la
   llave de los JWT.
3. Si el usuario ya tenía una terminal abierta, la anterior se cierra con
   `otra_sesion`.
4. Abre SSH a `TERMINAL_SSH_HOST` como el `username` de la sesión, verificando
   la llave del servidor contra `TERMINAL_KNOWN_HOSTS`. El navegador no puede
   elegir host ni usuario.
5. keyboard-interactive: las preguntas de sshd («Password:» y, en el primer
   ingreso, el cambio de clave) aparecen en la terminal y el usuario responde
   ahí. La clave no se guarda ni se registra.
6. Con la PTY abierta, copia en los dos sentidos: `entrada` → SSH y salida →
   marcos binarios. `tamano` cambia el tamaño de la PTY.
7. Cierra a los 15 minutos sin escribir (`inactividad`) o a las 2 horas
   (`tiempo_maximo`). Registra inicio y fin, nunca el contenido.

| Archivo           | Qué hace                                                        |
| ----------------- | --------------------------------------------------------------- |
| `app/main.py`     | El endpoint: Origin, sesión con la API, registro, logs y cierre |
| `app/sesion.py`   | El puente WebSocket ↔ SSH, los tiempos y una sesión por usuario |
| `app/ssh.py`      | La conexión SSH y las preguntas keyboard-interactive            |
| `app/api.py`      | `GET /api/me` con la cookie del usuario                         |
| `app/mensajes.py` | Los mensajes del WebSocket                                      |
| `app/config.py`   | Variables `TERMINAL_*`                                          |

## Variables

| Variable               | Por defecto                           |
| ---------------------- | ------------------------------------- |
| `TERMINAL_ORIGEN`      | `https://training.apolo.eafit.edu.co` |
| `TERMINAL_API_URL`     | `http://api:8000`                     |
| `TERMINAL_SSH_HOST`    | `apolo-training.apolo.eafit.edu.co`   |
| `TERMINAL_SSH_PUERTO`  | `22`                                  |
| `TERMINAL_KNOWN_HOSTS` | `/run/terminal/known_hosts`           |
| `TERMINAL_INACTIVIDAD` | `900` (segundos)                      |
| `TERMINAL_MAXIMO`      | `7200` (segundos)                     |

## Un solo proceso

El registro de sesiones vive en memoria. Con dos procesos, cada uno tendría el
suyo y un usuario podría abrir una terminal en cada uno. Por eso la imagen
corre uvicorn sin `--workers`: un proceso con asyncio atiende muchas terminales
a la vez, porque casi todo el tiempo está esperando red.

## Pruebas

```bash
cd terminal
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

No necesitan la API, la VM ni la VPN: `create_app()` recibe una API y un SSH
falsos. `tests/test_integracion.py` levanta además un servidor SSH de verdad
(asyncssh) en el mismo proceso, que pregunta «Password:» como sshd.

## La llave de la VM de práctica (known_hosts)

El gateway no se conecta si la llave del servidor no está en `known_hosts`: así
un impostor en el camino no recibe las contraseñas. La llave se revisa a mano
una vez, comparando dos huellas:

```bash
# En la VM de práctica: la huella real.
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
# Desde donde correrá el gateway: la llave que anuncia, y su huella.
ssh-keyscan -t ed25519 <host> > known_hosts
ssh-keygen -lf known_hosts
```

Si las huellas coinciden, `known_hosts` sirve. `<host>` debe ser el mismo valor
de `TERMINAL_SSH_HOST` (nombre o IP). En la 117 va en
`/srv/apolo-training/terminal/known_hosts` (root, 644); la carpeta la crea el
rol `docker`.

## La 117

El servicio `terminal` de [`deploy/compose.yaml`](../deploy/compose.yaml) no
publica puertos: el proxy (nginx, W-05) le pasa `/ws/terminal` por la red `interna`, y
sale a la VM de práctica por la red `salida`. Corre sin root, con el sistema de
archivos de solo lectura y sin capacidades. Requisitos en la VM de práctica:
`KbdInteractiveAuthentication yes` para los grupos `apolo2` y `apolo3` (rol
`base`).
