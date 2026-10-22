# ansible

Roles de la VM de práctica y de la plataforma. IPs, usuarios y contraseñas van
en Ansible Vault, nunca en claro.

| Archivo                    | Qué es                                                                           |
| -------------------------- | -------------------------------------------------------------------------------- |
| `inventory.ini`            | Máquinas y usuario de conexión (**cifrado**)                                     |
| `group_vars/all/vault.yml` | Admins, llaves, IPs y contraseñas de sudo y de MariaDB (**cifrado**)             |
| `group_vars/*/vars.yml`    | Variables; solo referencian las del Vault                                        |
| `site.yml`                 | Qué rol se aplica a qué grupo                                                    |
| `roles/base`               | Admins solo con llave y sshd sin root (contraseña solo para `apolo2` y `apolo3`) |
| `roles/slurm`              | Slurm de un nodo: munge, MariaDB, slurmdbd, slurmctld y slurmd con cgroups       |

## Requisitos

- VPN activa, colecciones `ansible.posix`, `community.general` y `community.mysql`.
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
| D      | Salida    | Rechaza todo lo demás                                                             |

Las IPs están en el Vault y las listas en `group_vars/practica/vars.yml`. Los
códigos son los de la solicitud de firewall. Las reglas F existen porque el
perimetral no ve el tráfico dentro de la misma subred.

Si una regla deja sin acceso, desde la consola de Proxmox:
`sudo systemctl stop nftables` (vacía las reglas).

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
slurmctld y slurmd. Los repositorios (CRB, EPEL, OpenHPC 3) los pone `base`.
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
