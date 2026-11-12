# ansible

Roles de la VM de práctica y de la plataforma. IPs, usuarios y contraseñas van
en Ansible Vault, nunca en claro.

| Archivo                    | Qué es                                                                              |
| -------------------------- | ----------------------------------------------------------------------------------- |
| `inventory.ini`            | Máquinas y usuario de conexión (**cifrado**)                                        |
| `group_vars/all/vault.yml` | Admins, llaves, IPs y contraseñas de sudo y de MariaDB (**cifrado**)                |
| `group_vars/*/vars.yml`    | Variables; solo referencian las del Vault                                           |
| `site.yml`                 | Qué rol se aplica a qué grupo                                                       |
| `roles/base`               | Admins solo con llave y sshd sin root (contraseña solo para `apolo2` y `apolo3`)    |
| `roles/slurm`              | Slurm de un nodo: munge, MariaDB, slurmdbd, slurmctld y slurmd con cgroups          |
| `roles/docker`             | Docker Engine y Compose de la plataforma (117), DOCKER-USER y `/srv/apolo-training` |
| `roles/certbot`            | Certificado TLS de Let's Encrypt de la plataforma y su renovación automática        |

`site.yml` aplica `base` y `slurm` al grupo `practica`, y `base`, `docker` y
`certbot` al grupo `web` (la 117).

## Requisitos

- VPN activa, colecciones `ansible.posix`, `community.general`, `community.mysql` y `community.docker`.
- `ansible/.vault_pass` información privada

## Uso

```bash
ansible-playbook site.yml --check --diff   # simular
ansible-playbook site.yml --diff           # aplicar (la segunda vez: changed=0)
ansible-vault edit group_vars/all/vault.yml   # agregar admins o llaves
```

### Firewall (nftables)

firewalld queda enmascarado y el firewall de la VM es un solo archivo,
`/etc/sysconfig/nftables.conf` (tabla `inet apolo_training`). Entrada y salida
son "todo prohibido salvo lo permitido"; lo rechazado recibe respuesta
inmediata (`reject`), así que `curl` o `ping` fallan al instante.

| Regla  | Dirección | Qué hace                                                                          |
| ------ | --------- | --------------------------------------------------------------------------------- |
| F1     | Entrada   | SSH y ping solo desde la VPN y la plataforma (117)                                |
| F2     | Entrada   | Rechaza todo lo demás                                                             |
| F3–F5  | Salida    | Rechaza FreeIPA, el hipervisor y la red de servicios, antes que cualquier permiso |
| S1, S2 | Salida    | DNS y NTP institucionales                                                         |
| —      | Salida    | HTTPS a la 117 (sincronización de laboratorios)                                   |
| S4     | Salida    | Web (80/443) hasta `base_internet_hasta`; después se cierra sola                  |
| S5     | Salida    | HTTPS (443) sin fecha, solo en la 117 (`base_salida_https_permanente`)            |
| D      | Salida    | Rechaza todo lo demás                                                             |

Las IPs están en el Vault y las listas en `group_vars/*/vars.yml`. Los
códigos son los de la solicitud de firewall. Las reglas F existen porque el
perimetral no ve el tráfico dentro de la misma subred.

Si una regla deja sin acceso, desde la consola de Proxmox:
`sudo systemctl stop nftables` (vacía las reglas). En la 117 eso también borra
las reglas de Docker: después, `sudo systemctl restart docker`.

El handler aplica el archivo con `nft -f` y no con `systemctl reload`, que en
Rocky 9 hace `flush ruleset` y borraría las tablas de Docker. El archivo solo
reemplaza la tabla `apolo_training`.

### sshd y fail2ban (116)

El gateway de terminal de la 117 abre todas las sesiones de la plataforma
desde la misma IP. En la 116 (`group_vars/practica`), sshd y fail2ban lo
tienen en cuenta (I-09):

| Qué               | Cómo queda                                   | Por qué                                                                             |
| ----------------- | -------------------------------------------- | ----------------------------------------------------------------------------------- |
| `MaxStartups`     | `30:50:60`                                   | Por defecto (`10:30:100`) sshd empieza a rechazar a la 10.ª conexión sin autenticar |
| `MaxSessions`     | `10`                                         | Sesiones por conexión                                                               |
| `ClientAlive*`    | Cada 60 s, corta tras 3 sin respuesta        | Libera en ~3 min una conexión muerta (VPN caída, portátil cerrado)                  |
| Banner            | `/etc/issue.net` (`base_banner`)             | Aparece antes de la clave, también en la terminal de la plataforma                  |
| fail2ban (`sshd`) | 5 claves erradas en 10 min: 15 min bloqueado | Igual que el bloqueo de la plataforma                                               |
| `ignoreip`        | La 117 (`base_fail2ban_ignorar`)             | Bloquearla cortaría la terminal a todos; el límite de intentos lo pone el gateway   |

- fail2ban se instala sin `fail2ban-firewalld` (firewalld está enmascarado):
  los bloqueos van en su propia tabla, `inet f2b-table`, que el handler de
  nftables no toca.
- Viene de EPEL: hay que aplicarlo mientras la 116 tenga salida web (S4).
- En la 117 nada de esto cambia: los valores por defecto son vacíos.

Verificación en la 116:

```bash
sudo sshd -T | grep -Ei 'maxstartups|maxsessions|clientalive|banner'
sudo fail2ban-client status sshd                 # Banned IP list
sudo fail2ban-client get sshd ignoreip           # incluye la IP de la 117
sudo nft list table inet f2b-table               # los bloqueos activos
sudo fail2ban-client set sshd unbanip <ip>       # desbloquear a alguien
```

### SELinux, hora y actualizaciones

| Qué           | Cómo queda                                                     | Por qué                                                                    |
| ------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------- |
| SELinux       | `enforcing`, política `targeted`                               | Limita lo que puede hacer un servicio comprometido, aunque corra como root |
| chrony        | Solo el NTP institucional (`base_ntp_servidores`), sin `pool`  | munge y Slurm fallan si la hora se desfasa                                 |
| dnf-automatic | `upgrade_type = security`, `apply_updates = yes`, timer diario | Parches de seguridad sin romper Slurm ni OpenHPC con otras actualizaciones |

- El rol instala `python3-libselinux`, que necesita el módulo de SELinux.
- Si SELinux estaba en `disabled`, el playbook se detiene: hay que reiniciar
  la VM y volver a correrlo.
- dnf-automatic necesita salida web (S4). Cuando S4 se cierre, deja de
  actualizar hasta que haya un espejo interno o un permiso solo hacia los
  repositorios de Rocky.

Verificación en la VM:

```bash
getenforce                                    # Enforcing
chronyc -n sources                            # ^* en el NTP institucional
systemctl list-timers dnf-automatic.timer     # próxima ejecución
```

### Slurm

Un solo nodo hace de controlador, de nodo de cómputo y de base de
contabilidad: munge, MariaDB (`127.0.0.1`, base `slurm_acct_db`), slurmdbd,
slurmctld y slurmd. CRB y EPEL los pone `base`; OpenHPC 3, este mismo rol.
La contraseña del usuario `slurm` de MariaDB es `vault_slurm_bd_password`.

| Qué                  | Cómo queda                                      | Por qué                                                                 |
| -------------------- | ----------------------------------------------- | ----------------------------------------------------------------------- |
| cgroups              | `proctrack/cgroup`, `task/cgroup,task/affinity` | Limitan núcleos y memoria por trabajo; `jobacct_gather/cgroup` mide uso |
| Swap                 | `ConstrainSwapSpace=yes`, `AllowedSwapSpace=0`  | La VM tiene 5 GB de swap; sin esto el trabajo usa swap en vez de OOM    |
| Memoria              | `RealMemory=8700`, `DefMemPerCPU=2000`          | Deja ~3 GB al sistema; sin `--mem` un trabajo no reserva todo el nodo   |
| Partición `training` | `DefaultTime=00:10:00`, `MaxTime=01:00:00`      | Laboratorios cortos con 4 núcleos compartidos                           |
| Epilog               | Sin `slurm.epilog.clean` de OpenHPC             | Mataría las sesiones SSH del usuario al terminar su último trabajo      |
| `slurmdbd.conf`      | `600`, dueño `slurm`                            | Tiene la contraseña; slurmdbd no arranca con otros permisos             |

- `slurm.conf` sale de una plantilla propia completa, no de `slurm.conf.ohpc`:
  la de OpenHPC ya trae opciones que, repetidas, dejan activo el valor viejo.
- Los valores que cambian (nodo, memoria, partición) están en
  `roles/slurm/defaults/main.yml`.

Verificación en la VM:

```bash
sinfo                                                    # training, nodo idle
srun -c 1 nproc                                          # 1
srun --mem=200M python3 -c "x = b'x' * (500*1024*1024)"  # oom_kill
sacct --format=JobID,State,ReqMem,MaxRSS,ExitCode        # OUT_OF_MEMORY
```

### Docker (117)

Docker CE del repositorio oficial para RHEL (se quitan podman, buildah y runc),
con el plugin de Compose. Solo los administradores están en el grupo `docker`,
que equivale a ser root.

| Qué              | Cómo queda                                                                   | Por qué                                                                                  |
| ---------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `daemon.json`    | `json-file` 10m × 3, `live-restore`, `selinux-enabled`                       | Logs acotados; reiniciar el daemon no tumba contenedores; Docker CE trae SELinux apagado |
| Reenvío (`base`) | `base_reenvio_politica: accept`                                              | Los puertos publicados y la salida de los contenedores pasan por forward                 |
| DOCKER-USER      | 443 publicado solo desde `docker_443_permitido`; resto, rechazado            | Docker publica con DNAT y se salta la cadena `entrada` de nftables                       |
| Salida           | Contenedores sin acceso a `docker_salida_bloqueada`                          | Lo mismo que F3–F5 para la VM                                                            |
| Datos            | `/srv/apolo-training/{media,pgdata,backups,tls,secrets}`, `container_file_t` | En el compose, `:Z` si el volumen es de un contenedor, `:z` si se comparte               |

- Las reglas de DOCKER-USER están en `/usr/local/sbin/docker-user` y las pone
  la unidad `docker-user.service` después de docker (y otra vez si docker se
  reinicia). Solo filtran lo que entra por la interfaz externa, para no cortar
  la salida de los contenedores.
- Solo el proxy publica puertos (`443`); `api`, `db` y `terminal` van en la red
  interna del compose sin `ports:`.
- El proyecto de prueba (`/srv/apolo-training/prueba`) era un nginx en el 443
  para probar el rol antes del proxy. Con el proxy real (W-05) va
  `docker_prueba: absent`, que lo baja y borra la carpeta.
- `docker pull`, el repo de Docker y certbot salen por el 443. En la 117 eso es
  la S5, sin fecha; la S4 (también el 80) se cierra en `base_internet_hasta`.
- Los secretos de Compose (`docker_secretos`) se escriben desde el Vault con
  `no_log`; los de la API son del uid 10001 (usuario `api` de la imagen), modo
  `0400`. `docker_known_hosts` es la llave de la VM de práctica para el gateway
  de terminal, con la huella revisada a mano en el comentario.

Verificación en la 117 y desde la VPN:

```bash
docker info && docker compose version     # como administrador, sin sudo
docker run --rm alpine cat /proc/self/attr/current   # ...container_t...
sudo iptables -S DOCKER-USER
nmap -Pn -p- <ip-de-la-117>               # desde la VPN: solo 22, 80 y 443 abiertos
```

### Certificado TLS (117)

Let's Encrypt con el reto HTTP-01: certbot (en el host, de EPEL) deja el reto
en `/srv/apolo-training/acme`, el proxy lo sirve en el 80 y Let's Encrypt lo
pide desde Internet. El certificado queda en `/etc/letsencrypt/live/<dominio>/`
y el script `/usr/local/sbin/apolo-training-tls-deploy` (deploy hook) copia
`fullchain.pem` y `privkey.pem` a `/srv/apolo-training/tls` (600, root) y
recarga nginx. No se monta `/etc/letsencrypt` en el contenedor: ahí también
está la llave de la cuenta de Let's Encrypt.

| Qué             | Cómo queda                                                  | Por qué                                           |
| --------------- | ----------------------------------------------------------- | ------------------------------------------------- |
| Emisión         | `certbot certonly --webroot`, solo si no existe (`creates`) | Idempotente: lo demás lo hace la renovación       |
| Renovación      | `certbot-renew.timer`, dos veces al día; renueva a 30 días  | El certificado dura 90 días                       |
| Provisional     | Autofirmado de 30 días, solo si `tls/` está vacío           | En una VM nueva, nginx no arranca sin certificado |
| Correo de la CA | `vault_certbot_correo`                                      | El repo es público                                |
| Salida          | 443 a Let's Encrypt por la S5                               | Sin ella la renovación falla en silencio          |

En una VM nueva, el orden es: `site.yml` (deja el provisional; la emisión
falla porque el proxy aún no corre), levantar el proyecto con
`docker compose up -d` y volver a correr `site.yml`, que ya emite el
certificado. Let's Encrypt no envía avisos de vencimiento: la fecha se vigila
con `certbot certificates`.

Verificación en la 117:

```bash
sudo certbot certificates                 # VALID: N days
systemctl list-timers certbot-renew.timer # próxima ejecución
sudo certbot renew --dry-run              # all simulated renewals succeeded
sudo nft list chain inet apolo_training salida   # S5 con counter
```
