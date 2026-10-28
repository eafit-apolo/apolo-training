# Inventario de los clústeres (A-04)

Datos de Apolo II y Apolo III para construir los perfiles de la VM de práctica y
escribir los módulos 3 (archivos), 5 (Slurm) y 7 (OnDemand). Se tomaron
directamente en cada login el 9 de octubre de 2026. Las salidas completas de
`module avail` y `module spider` están en [`inventario/`](inventario/).

No incluye nombres de servidores, de nodos ni de usuarios; esos datos están en
Affine.

## Apolo II frente a Apolo III

| Aspecto                     | Apolo II                                                                          | Apolo III                                                                         |
| --------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Login                       | `apolo.eafit.edu.co`                                                              | `apolo-3.eafit.edu.co`                                                            |
| Slurm                       | 25.11.4                                                                           | 24.11.5                                                                           |
| Partición por defecto       | `longjobs`                                                                        | **Ninguna** (todas con `Default=NO`): sin `-p` el trabajo no entra                |
| Particiones (tiempo máximo) | `bigmem`, `accel`, `accel-2` y `longjobs` 14 d; `learning` 3 d                    | `bigmem` 4 d, `longjobs` 6 d, `accel` 3 d                                         |
| Tiempo por defecto          | `00:00:00` en todas                                                               | 2 h en todas                                                                      |
| Restricción de grupos       | Ninguna (`AllowGroups=ALL`)                                                       | Ninguna (`AllowGroups=ALL`)                                                       |
| Toolchain por defecto       | `gnu15/15.2.0` + `openmpi5/5.0.10`                                                | `gnu14/14.2.0` + `openmpi5/5.0.7`                                                 |
| Módulos base                | `autotools`, `prun/2.2`, `hwloc/2.13.0`, `ucx/1.20.1`, `libfabric/1.18.0`, `ohpc` | `autotools`, `prun/2.2`, `hwloc/2.12.0`, `ucx/1.18.0`, `libfabric/1.18.0`, `ohpc` |
| Home                        | NFS desde el servidor de almacenamiento, montado con autofs                       | En el nodo maestro, exportado por NFS a los nodos                                 |
| Cuota del home              | Por **grupo**: 180 GB soft / 200 GB hard (valor habitual)                         | Por **usuario**: 150 GB soft / 200 GB hard, 7 días de gracia                      |
| Scratch                     | `/scratch` existe, pero hay que pedírselo a un administrador                      | `/scratch/<usuario>`, el usuario puede escribir                                   |
| Software compartido         | `/share/apps` (solo lectura)                                                      | `/share` (solo lectura)                                                           |
| Mensaje de bienvenida       | `/etc/motd` estático                                                              | Sin `/etc/motd`; script que lista los paquetes de módulos                         |
| OnDemand                    | No tiene                                                                          | Sí                                                                                |

## Particiones

Salida de `scontrol show partition`. Ninguna partición restringe grupos ni
cuentas (`AllowGroups=ALL`, `AllowAccounts=ALL`).

### Apolo II

Todas tienen `DefaultTime=00:00:00`, `PreemptMode=OFF` y la QOS
`apolo_anti-kidnapping`.

| Partición  | Por defecto | MaxTime     | DefMemPerCPU (MB) | MaxNodes   | Nodos | CPUs | Memoria total | GPUs |
| ---------- | ----------- | ----------- | ----------------: | ---------- | ----: | ---: | ------------: | ---: |
| `longjobs` | Sí          | 14-00:00:00 |              1875 | 3          |     9 |  288 |       573982M |    — |
| `bigmem`   | No          | 14-00:00:00 |              8000 | Sin límite |     2 |   48 |       773152M |    — |
| `accel`    | No          | 14-00:00:00 |              1875 | Sin límite |     1 |   32 |        64052M |    4 |
| `accel-2`  | No          | 14-00:00:00 |              1875 | Sin límite |     1 |   32 |       128113M |    3 |
| `learning` | No          | 3-00:00:00  |              1900 | Sin límite |     1 |   32 |        64052M |    — |

### Apolo III

Todas tienen `DefaultTime=02:00:00`, `PreemptMode=REQUEUE` y ninguna QOS de
partición.

| Partición  | Por defecto | MaxTime    | DefMemPerCPU (MB) | MaxNodes | Nodos | CPUs | Memoria total | GPUs |
| ---------- | ----------- | ---------- | ----------------: | -------: | ----: | ---: | ------------: | ---: |
| `bigmem`   | No          | 4-00:00:00 |              7500 |        2 |     2 |  128 |      1030962M |    — |
| `longjobs` | No          | 6-00:00:00 |              5700 |        2 |     2 |  128 |          754G |    — |
| `accel`    | No          | 3-00:00:00 |              4000 |        2 |     1 |   64 |          251G |    — |

`accel` no reporta GPUs en `TRES` (no aparece `gres/gpu`).

## Módulos

`module list` en una sesión nueva carga lo mismo en los dos clústeres, cambiando
las versiones:

| Clúster   | Módulos cargados al entrar                                                                                           |
| --------- | -------------------------------------------------------------------------------------------------------------------- |
| Apolo II  | `autotools`, `prun/2.2`, `gnu15/15.2.0`, `hwloc/2.13.0`, `ucx/1.20.1`, `libfabric/1.18.0`, `openmpi5/5.0.10`, `ohpc` |
| Apolo III | `autotools`, `prun/2.2`, `gnu14/14.2.0`, `hwloc/2.12.0`, `ucx/1.18.0`, `libfabric/1.18.0`, `openmpi5/5.0.7`, `ohpc`  |

- **Comunes y útiles para el curso:** `py3-numpy/1.26.4`, `miniconda3/25.11.1`,
  `R/4.6.0`, `matlab/R2025b`, `apptainer`, `cuda`, `spack`.
- **Apolo III** tiene además `miniconda3/25.5.1` (versión por defecto), Intel
  2023 a 2025, `gnu12/12.2.0`, `ansys`, `gromacs` y `code-server`.
- **Apolo III esconde parte del árbol:** `module spider` muestra módulos que
  `module avail` no lista (por ejemplo `alphafold3`, `advisor` y los
  componentes de Intel). Para verlos hay que hacer antes
  `module use /opt/ohpc/pub/moduledeps/<paquete>`, como indica el mensaje de
  bienvenida.

| Archivo                                                           | Contenido                    |
| ----------------------------------------------------------------- | ---------------------------- |
| [`apolo2-module-avail.txt`](inventario/apolo2-module-avail.txt)   | `module avail` en Apolo II   |
| [`apolo2-module-spider.txt`](inventario/apolo2-module-spider.txt) | `module spider` en Apolo II  |
| [`apolo3-module-avail.txt`](inventario/apolo3-module-avail.txt)   | `module avail` en Apolo III  |
| [`apolo3-module-spider.txt`](inventario/apolo3-module-spider.txt) | `module spider` en Apolo III |

## Almacenamiento

### Apolo II

| Ruta              | Qué es                                              | Usuario nuevo                           |
| ----------------- | --------------------------------------------------- | --------------------------------------- |
| `/home/<usuario>` | NFS desde el servidor de almacenamiento, con autofs | **Sí**, automático                      |
| `/share/apps`     | Software compartido por NFS                         | Solo para usar programas; no para datos |
| `/scratch`        | Mapa autofs, existe en el login y en los nodos      | **No**; se le pide a un administrador   |
| `/shared-dirs`    | Mapa autofs, existe en el login y en los nodos      | **No**; igual que `/scratch`            |
| `/tmp`            | Local de cada máquina                               | Sí, pero no es compartido               |

### Apolo III

| Ruta                 | Qué es                                                        | Tamaño                            | Permisos                                                  | Usuario nuevo                                       |
| -------------------- | ------------------------------------------------------------- | --------------------------------- | --------------------------------------------------------- | --------------------------------------------------- |
| `/home/<usuario>`    | En el nodo maestro (XFS), exportado por NFS                   | 37 TB                             | Del usuario                                               | **Sí**, con cuota de 150 / 200 GB                   |
| `/scratch/<usuario>` | Volumen propio (XFS)                                          | 9.1 TB (5 % usado)                | `/scratch` es 1777 (sticky); cada carpeta es `drwx------` | **Sí**, puede escribir; falta saber si se crea sola |
| `/share`             | Software compartido (`apps`, `bin`, `lib`…)                   | 4.3 TB, compartidos con `/vol001` | `root 755`                                                | Solo lectura (usar programas)                       |
| `/vol001`            | El mismo volumen que `/share`; instaladores de administración | ídem                              | `root 755`                                                | No es para usuarios                                 |
| `/projects`          | Disco local del nodo maestro                                  | 700 GB (75 % usado)               | `root root 770` + sticky                                  | **No**; ni siquiera puede listarlo                  |

## Cuotas del home

### Apolo II

| Dato              | Valor                                                                                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Sistema           | Linux con XFS; la cuota cubre todo el volumen exportado: homes y software                                                                  |
| Tipo              | **Solo por grupo.** No hay cuota por usuario ni por proyecto                                                                               |
| Qué cuenta        | Los archivos suman a la cuota del **grupo dueño del archivo**, normalmente el grupo primario del usuario. Los miembros comparten el límite |
| Límite habitual   | **180 GB soft / 200 GB hard por grupo**                                                                                                    |
| Grupos contenedor | 1 MB / 2 MB (`eafit`, `universidades`, `industria`…): en la práctica no sirven para guardar datos                                          |
| Excepciones       | Grupos de investigación grandes con límites a medida, de 2 TB a 11 TB                                                                      |
| Sin límite        | Grupos con 0 / 0, entre ellos los personales. Un grupo nuevo al que nadie le asigna límite **queda ilimitado**                             |
| Usuario nuevo     | Hereda la cuota de su grupo primario. A un grupo nuevo un administrador le asigna a mano el valor habitual de 180 / 200 GB                 |

### Apolo III

| Dato               | Valor                                                                                   |
| ------------------ | --------------------------------------------------------------------------------------- |
| Dónde              | `/home` en el nodo maestro: XFS, 37 TB, exportado por NFS a los nodos                   |
| Tipo               | **Solo por usuario** (`uquota`). Las cuotas de grupo y de proyecto están apagadas       |
| Límite por defecto | **150 GB soft / 200 GB hard**; se aplica a los usuarios nuevos                          |
| Inodos             | Sin límite                                                                              |
| Gracia             | 7 días                                                                                  |
| Excepciones        | Tres cuentas con límites a medida, de 500 GB a 8 TB                                     |
| Pendiente          | Algunas cuentas antiguas tienen solo límite hard (2, 15 o 100 GB) de origen desconocido |

## Mensaje de bienvenida

- **Apolo II:** `/etc/motd` estático con el banner «APOLO 2 CLUSTER -
  UNIVERSIDAD EAFIT». Pide usar los recursos con eficiencia y enviar los
  trabajos con Slurm, y da el correo de soporte `apolo@eafit.edu.co`.
- **Apolo III:** no tiene `/etc/motd`. Un script en `/etc/profile.d/` lista los
  paquetes de módulos al entrar e indica
  `module use /opt/ohpc/pub/moduledeps/<paquete>`.

## Qué implica para el curso

- **Módulo 3:** las pestañas cambian de verdad. En Apolo II la cuota es del
  grupo y la comparten todos sus miembros; en Apolo III es de cada usuario.
  `quota -s` muestra cosas distintas en cada clúster.
- **Módulo 3:** el scratch solo se enseña en Apolo III; en Apolo II hay que
  pedirlo.
- **Módulo 4:** en Apolo III hay que explicar `module use` antes de
  `module spider`, porque parte del software no aparece en `module avail`.
- **Módulo 4:** el toolchain por defecto es distinto (`gnu15` en Apolo II,
  `gnu14` en Apolo III), pero `module load py3-numpy` funciona igual en los dos
  y `gnu14` existe en ambos. Los ejemplos del curso no nombran el compilador.
- **Módulo 5:** confirma que en Apolo III no hay partición por defecto; los
  ejemplos llevan `-p`. El tiempo por defecto es 2 h en Apolo III.
- **Módulo 7:** OnDemand solo existe en Apolo III. La graduación con OnDemand
  (V-07) no aplica tal cual a los usuarios de Apolo II; hay que definir su
  alternativa en el mapa.

## Pendientes

| Falta                                                      | Afecta   |
| ---------------------------------------------------------- | -------- |
| Si `/scratch/<usuario>` se crea solo en Apolo III          | Módulo 3 |
| Qué límite real recibe un trabajo sin `--time` en Apolo II | Módulo 5 |

## Aprobación

- [x] Partición por defecto de Apolo III confirmada (`scontrol show partition`).
- [x] Tipo y límites de cuota de Apolo II confirmados por un administrador.
- [x] Tabla sin pendientes.
- [ ] Revisado por Juan.
