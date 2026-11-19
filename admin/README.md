# admin

`apolo-training-admin`: altas y bajas de los usuarios del curso, en la VM de
práctica (116) y en la plataforma (117), con un solo comando. Corre como root
en la 116 con el Python 3.9 de Rocky 9 y solo usa la biblioteca estándar.

El subcomando `reporte` y el timer de sincronización de laboratorios
(`POST /api/internal/labs`) son otra tarea y todavía no están.

| Archivo                   | Qué es                                                                |
| ------------------------- | --------------------------------------------------------------------- |
| `apolo_training_admin.py` | El comando; se instala como `/usr/sbin/apolo-training-admin`          |
| `admin.conf.example`      | Plantilla de `/etc/apolo-training/admin.conf`                         |
| `systemd/`                | Timer diario que archiva los homes de las bajas de hace 30 días o más |
| `tests/`                  | Pruebas con dobles de los comandos y una plataforma HTTP local        |

## Uso

```bash
apolo-training-admin alta ana --cluster apolo2 --nombre "Ana Pérez" --correo ana@eafit.edu.co
apolo-training-admin baja ana
apolo-training-admin archivar
```

`--idioma en` en la alta deja la plataforma en inglés.

## Qué hace

**alta** (todo o nada):

1. `useradd -m -G <cluster>`, clave temporal aleatoria con `chpasswd` (por
   stdin, nunca en la línea de comandos) y `chage -d 0`.
2. `sacctmgr add user` en `curso-<cluster>`; hereda la QOS `curso`.
3. Perfil en `/etc/apolo-training/usuarios/<usuario>` (lo lee
   `/etc/profile.d/apolo-training.sh`).
4. `apolo-training preparar` como el usuario: material del curso en
   `~/apolo-training`.
5. `POST /api/internal/usuarios` con el token de servicio y la **misma** clave
   temporal. La plataforma también la pide cambiar en el primer ingreso.

Antes de tocar nada revisa que el usuario no exista, que la URL sea https y
que el token y el verificador estén en su sitio. Si falla un paso (o Ctrl+C),
deshace los anteriores en orden inverso (`sacctmgr delete`, `userdel -r`,
borrar el perfil) y no queda ninguna cuenta a medias. La clave se imprime al
final para entregársela al usuario.

**baja** (se puede repetir; completa lo que falte):

1. `usermod -L -e 1`: la cuenta vence y PAM rechaza todo ingreso, también
   con llave SSH. `pkill -KILL -u` corta las sesiones abiertas.
2. `scancel -u` y `sacctmgr delete user` (reintenta mientras haya trabajos
   terminando).
3. Marca `/var/lib/apolo-training/bajas/<usuario>` con la fecha.
4. `PATCH /api/internal/usuarios/<usuario>` con `activo=false` (la API revoca
   sus sesiones).

Solo da de baja a quien esté en el grupo `apolo2` o `apolo3`. Si falla la
plataforma, la VM ya quedó bloqueada y basta repetir la baja.

**archivar** (timer diario, 03:30): para cada marca de 30 días o más, si la
cuenta sigue bloqueada, empaqueta el home en
`/var/lib/apolo-training/archivo/<usuario>-<fecha>.tar.gz` (600), lo borra y
quita el perfil y la marca. La cuenta Unix queda bloqueada, no se borra: así
su UID no se reutiliza y el historial de Slurm sigue siendo suyo.

## Instalación en la 116

La hace el rol `admin` de Ansible (`ansible-playbook site.yml`), que toma el
token de `vault_token_servicio`; ver [`ansible/README.md`](../ansible/README.md).
A mano sería:

```bash
install -m 700 admin/apolo_training_admin.py /usr/sbin/apolo-training-admin
install -m 600 admin/admin.conf.example /etc/apolo-training/admin.conf   # y editar url
install -m 600 /dev/null /etc/apolo-training/token                       # y pegar el token
install -m 644 admin/systemd/apolo-training-admin-archivar.* /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now apolo-training-admin-archivar.timer
```

El token es el mismo que tiene la API para las rutas `/internal/*`; nunca va
al repositorio.

## Pruebas

```bash
cd admin
python -m pip install -r requirements-dev.txt
python -m pytest
```

No necesitan root, Slurm ni la API: `tests/bin/falso` reemplaza a `useradd`,
`sacctmgr`, etc. y registra cada llamada, y `conftest.py` levanta una
plataforma HTTP en 127.0.0.1 que responde lo que pida cada prueba (201, 409,
503, sin conexión…).
