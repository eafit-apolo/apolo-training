# Perfiles de la VM de práctica (P-01)

Qué cambia en la VM de práctica (`apolo-training.apolo.eafit.edu.co`) según el
clúster del usuario y qué se queda igual. Parte del inventario
([`inventario.md`](inventario.md), A-04) y del mapa del curso
([`../content/mapa.md`](../content/mapa.md), A-12). Lo implementan P-02
(particiones), P-03 (perfil al entrar), P-04 (laboratorio por perfil), I-06
(módulos), I-08 (grupos, cuentas y QOS), V-04 (altas) y V-06 (instalación en
los clústeres).

## Cómo funciona

- Cada usuario tiene un perfil, `apolo2` o `apolo3`: el clúster donde tiene su
  cuenta real. Son los mismos valores del campo `cluster` de `usuarios` en el
  diseño ([`diseno/modelo-datos.md`](diseno/modelo-datos.md)) y del esquema
  `Cluster` de la API. Lo fija `apolo-training-admin alta --cluster` (flujo de
  altas en [`diseno/flujos.md`](diseno/flujos.md)).
- El perfil decide su grupo Unix y su cuenta de Slurm en la VM, las particiones
  que ve, la partición por defecto, el prompt y el mensaje de bienvenida.
- Slurm, la QOS del curso, los módulos, el verificador, las prácticas y `pi.py`
  son iguales para los dos.
- Lo que la VM no puede imitar (cuotas, scratch, tiempos y memoria por defecto,
  OnDemand) se explica en las pestañas Apolo II / Apolo III de cada lección.

## Los dos perfiles

| Aspecto                                           | Apolo II (`apolo2`)                                                           | Apolo III (`apolo3`)                                                             | En la VM                                                                                             |
| ------------------------------------------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Login real                                        | `apolo.eafit.edu.co`                                                          | `apolo-3.eafit.edu.co`                                                           | Se imita: prompt y mensaje de bienvenida                                                             |
| Grupo Unix y cuenta de Slurm                      | `apolo2`, `curso-apolo2`                                                      | `apolo3`, `curso-apolo3`                                                         | Solo existen en la VM (I-08)                                                                         |
| Particiones que ve en `sinfo`                     | `longjobs`, `bigmem`, `accel`, `accel-2`, `learning`                          | `bigmem`, `longjobs`, `accel`                                                    | Se imita con `AllowGroups` (P-02). `longjobs-smt` no se crea: un usuario normal de Apolo II no la ve |
| Partición por defecto                             | `longjobs`                                                                    | Ninguna: sin `-p` el trabajo no entra                                            | Se imita (ver «Partición por defecto»)                                                               |
| Tiempo máximo y por defecto                       | 14 días (`learning`, 3); por defecto `00:00:00`                               | 4, 6 y 3 días; por defecto 2 h                                                   | Solo texto: en la VM, 15 minutos para todos (QOS `curso`)                                            |
| Memoria por defecto (`DefMemPerCPU`)              | 1875 MB en `longjobs`, 8000 en `bigmem`, 1900 en `learning`                   | 7500 MB en `bigmem`, 5700 en `longjobs`, 4000 en `accel`                         | Solo texto: la VM es un solo nodo pequeño                                                            |
| Límite de memoria y de núcleos                    | Sí                                                                            | No                                                                               | La VM limita los dos en los dos perfiles; ver «Aviso de Apolo III (P-05)»                            |
| Uso real de CPU en `sacct` (`TotalCPU`, `MaxRSS`) | Sí                                                                            | No                                                                               | La VM lo registra en los dos perfiles; ver «Aviso de Apolo III (P-05)»                               |
| Toolchain al entrar                               | `gnu15/15.2.0` + `openmpi5/5.0.10`                                            | `gnu14/14.2.0` + `openmpi5/5.0.7`                                                | Igual para los dos: `gnu14/14.2.0` + `openmpi5/5.0.7` (ver «Módulos»)                                |
| `MODULEPATH` al entrar                            | `/opt/ohpc/pub/modulefiles`, `moduledeps/gnu15` y `moduledeps/gnu15-openmpi5` | `/opt/ohpc/pub/modulefiles`, `moduledeps/gnu14` y `moduledeps/gnu14-openmpi5`    | Igual para los dos: el de Apolo III                                                                  |
| Software que pide `module use`                    | No                                                                            | Parte del árbol solo aparece con `module use /opt/ohpc/pub/moduledeps/<paquete>` | Solo texto: ninguna práctica lo necesita                                                             |
| Módulos del curso                                 | `py3-numpy/1.26.4` y `apolo-training`, sin `module use`                       | Igual                                                                            | Igual                                                                                                |
| Home                                              | NFS con autofs                                                                | En el nodo maestro, por NFS                                                      | Solo texto: en la VM es local                                                                        |
| Cuota del home                                    | Por grupo: 180 GB soft / 200 GB hard                                          | Por usuario: 150 GB soft / 200 GB hard, 7 días de gracia                         | Solo texto: `quota -s` en la VM no muestra la cuota real                                             |
| Scratch                                           | `/scratch` se le pide a un administrador                                      | `/scratch/<usuario>`                                                             | Solo texto                                                                                           |
| Software compartido                               | `/share/apps`                                                                 | `/share`                                                                         | Solo texto                                                                                           |
| Mensaje de bienvenida                             | `/etc/motd` estático                                                          | Script que lista los paquetes de módulos                                         | Mensaje propio del curso con el login real                                                           |
| OnDemand                                          | No tiene                                                                      | Sí                                                                               | Fuera del curso: aviso en `m07/vscode`                                                               |
| Versión de Slurm                                  | 25.11                                                                         | 24.11                                                                            | La de OpenHPC de la VM, igual para los dos                                                           |

## Partición por defecto

En la VM, `longjobs` es la partición por defecto (P-02): un usuario `apolo2`
que envía sin `-p` cae en `longjobs`, como en Apolo II. Un usuario `apolo3`
recibe un error, como en Apolo III. Lo hace un `job_submit.lua` en la VM:
rechaza los trabajos sin partición de los miembros del grupo `apolo3`, con el
mensaje «Apolo III no tiene partición por defecto: indique una con -p».

- No se usan `SBATCH_PARTITION`, `SALLOC_PARTITION` ni `SLURM_PARTITION`: esas
  variables pisan el `#SBATCH --partition` del script, y el curso enseña a
  ponerlo ahí.
- Diferencia que queda: un usuario `apolo3` ve `longjobs*` con asterisco en
  `sinfo`. Se aclara en la pestaña Apolo III del módulo 5.
- Los comandos del curso llevan siempre `-p` (regla del mapa), así que la
  diferencia solo se nota si el usuario lo olvida.
- Si el Slurm de la VM no trae el plugin `job_submit/lua`, `longjobs` queda por
  defecto para los dos perfiles y la diferencia se explica solo en el módulo 5.

## Módulos

La VM no imita el toolchain de cada clúster: todos los usuarios entran con
`gnu14/14.2.0` + `openmpi5/5.0.7` (rol `lmod`, I-06), el entorno por defecto de
Apolo III.

- `gnu14` es el único compilador que existe en los dos clústeres. En Apolo II
  no es el de por defecto (`gnu15`), pero aparece en `module avail`.
- Lo que el curso enseña no depende del compilador: `module avail`, `spider`,
  `load`, `list` y `purge` funcionan igual, y `module load py3-numpy` encuentra
  `py3-numpy/1.26.4` con el toolchain por defecto de cada clúster.
- Diferencia que queda: un usuario `apolo2` ve `gnu14` en `module list` y en su
  clúster verá `gnu15`, con otras versiones de `openmpi5`, `hwloc` y `ucx`. Se
  aclara en la pestaña Apolo II de `m04/modulos`.
- Lmod no lee el perfil (`APOLO_TRAINING_CLUSTER`), así que el entorno es el
  mismo aunque el usuario no tenga perfil.

## Graduación

La graduación no se hace en la VM: es el primer trabajo del usuario en su
clúster real (`m07/graduacion`, V-07). Particiones decididas en el PR #15:

|                                   | Apolo II                           | Apolo III                        |
| --------------------------------- | ---------------------------------- | -------------------------------- |
| Comando                           | `sbatch -p learning graduacion.sh` | `sbatch -p bigmem graduacion.sh` |
| Memoria que apartaría sin `--mem` | 1900 MB por núcleo                 | 7500 MB por núcleo               |

`graduacion.sh` es igual en los dos clústeres: trabajo `curso-graduacion`, 1 o
2 núcleos, `--mem=1G`, un `--time` de pocos minutos (en Apolo II el tiempo por
defecto es `00:00:00`) y `pi.py` con numpy. La partición va en la línea de
comandos, no en el script, y no se fija nodo: Slurm lo escoge. El verificador
aprueba si el trabajo corrió en la partición de esta tabla para el clúster del
usuario, que lee de `APOLO_TRAINING_CLUSTER`.

## Archivo de perfil y variables

| Qué                | Dónde                                                                                            | Lo escribe                         | Lo lee                             |
| ------------------ | ------------------------------------------------------------------------------------------------ | ---------------------------------- | ---------------------------------- |
| Perfil del usuario | `/etc/apolo-training/usuarios/<usuario>`: una línea, `apolo2` o `apolo3`; dueño `root`, modo 644 | `apolo-training-admin alta` (V-04) | `/etc/profile.d/apolo-training.sh` |
| Script de entrada  | `/etc/profile.d/apolo-training.sh`                                                               | Rol `profiles` de Ansible (P-03)   | Cada sesión de shell               |

| Variable                 | Valor                     | Quién la pone                                                                                                                                           | Para qué                                                                                                 |
| ------------------------ | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `APOLO_TRAINING_CLUSTER` | `apolo2` o `apolo3`       | En la VM, `apolo-training.sh`; en Apolo II y Apolo III, el modulefile `apolo-training/1.0` que instala la V-06 en cada clúster (el de la VM no la pone) | Partición de la graduación y mensajes de Apolo III del verificador (P-05); laboratorio por perfil (P-04) |
| `APOLO_TRAINING`         | Carpeta de instalación    | Modulefile `apolo-training/1.0` (ya existe)                                                                                                             | El verificador encuentra `labs/`                                                                         |
| `APOLO_TRAINING_LANG`    | `es` (por defecto) o `en` | El usuario (ya existe)                                                                                                                                  | Idioma del verificador (el mensaje de bienvenida va siempre en inglés)                                   |

- **Prompt:** `[\u@\h \W (apolo3)]\$ `, el de Rocky con el perfil al final; por
  ejemplo, `[ana@apolo-training ~ (apolo3)]$`.
- **Mensaje de bienvenida**, siempre en inglés (P-03): el script corre antes
  que `~/.bash_profile` y `~/.bashrc`, donde el usuario pone
  `APOLO_TRAINING_LANG`, así que no puede leerla.

  ```text
  Apolo induction course · Practice VM
  Profile: Apolo III. Your real login is apolo-3.eafit.edu.co.
  Everything here is practice: a mistake only affects you.
  Platform: https://training.apolo.eafit.edu.co
  ```

- **Sin perfil válido:** si el archivo trae otro valor, o si el usuario está en
  el grupo `apolo2` o `apolo3` y no tiene archivo, el script muestra
  «You do not have a course profile (apolo2 or apolo3). Please contact an
  instructor.». No pone `APOLO_TRAINING_CLUSTER` ni el prompt, y quedan los
  módulos por defecto de la VM. A los administradores, sin archivo ni grupo del
  curso, no se les muestra nada.

## Qué se queda igual

- Slurm: la misma versión, cgroups, registro de uso y QOS `curso` (I-08).
- El verificador `apolo-training` y las siete prácticas.
- Los módulos: `gnu14` + `openmpi5` al entrar, `py3-numpy` y `apolo-training`.
- `pi.py`. En `curso.sh` solo cambia la partición (P-04): `module load` es el
  mismo en la VM y en los dos clústeres.
- El nombre de la máquina (`hostname`) y la práctica de VS Code.

## Dónde se explica lo que no se imita

| Diferencia                                                | Lección                                                                         |
| --------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Home, cuotas y scratch                                    | `m03/archivos`                                                                  |
| `module use` y el árbol escondido de Apolo III            | `m04/modulos`                                                                   |
| Toolchain de Apolo II (`gnu15`) frente al de la VM        | `m04/modulos`                                                                   |
| Partición, tiempo y memoria por defecto                   | `m05/trabajos`                                                                  |
| Apolo III sin límite de memoria ni registro de uso (P-05) | `m05/trabajos` y `m06/paralelismo`, con el texto de «Aviso de Apolo III (P-05)» |
| OnDemand                                                  | `m07/vscode`                                                                    |

## Aviso de Apolo III (P-05)

Apolo III hoy no limita la memoria ni los núcleos de un trabajo y no registra
su uso real: tiene solo `task/affinity` y no tiene `JobAcctGatherType`, así que
`TotalCPU` y `MaxRSS` salen vacíos en `sacct` (pruebas de la A-03 en
[`requisitos/`](requisitos/README.md)). La VM sí lo hace en los dos perfiles,
como Apolo II. Mientras siga así, la pestaña Apolo III de dos lecciones lo
explica y el verificador lo detecta.

### Texto para las lecciones

Va dentro del bloque `::: apolo3` de cada lección, después del resto de esa
pestaña. Sin comentarios HTML: el renderizador de la plataforma (F-04) podría
mostrarlos como texto.

`m05/trabajos` (C-07):

```markdown
**Diferencia con la VM:** hoy Apolo III no hace cumplir la memoria que pides ni
registra cuánta usó tu trabajo.

- El `OUT_OF_MEMORY` que viste en el laboratorio `memoria` pasa igual en
  Apolo II, pero no en Apolo III: si tu programa usa más de lo que pediste con
  `--mem`, Slurm no lo detiene.
- `--mem` sí cuenta para repartir los nodos. Pide una memoria cercana a la que
  usas: si te pasas, le quitas memoria a los otros trabajos del nodo, y si el
  nodo se queda sin memoria, el sistema puede terminar tu trabajo o el de otra
  persona.
- En `sacct`, `MaxRSS` y `TotalCPU` salen vacíos o en cero. `Elapsed` sí sirve,
  y `CPUTime` es lo reservado (duración × núcleos), no lo usado.
```

`m06/paralelismo` (C-08):

```markdown
**Diferencia con la VM:** hoy Apolo III no registra cuánto CPU usó tu trabajo,
así que ahí `apolo-training eficiencia JOBID` no puede calcular la eficiencia:
te avisa que no hay datos. Lo que comprobaste en los laboratorios `nucleos` y
`paralelo` vale igual para Apolo III.

- Slurm pone tu trabajo en los núcleos que reservaste, pero no lo encierra ahí:
  un programa que cambie su afinidad (por ejemplo, con `taskset`) puede usar
  núcleos de otros trabajos. Reserva con `--cpus-per-task` los núcleos que tu
  programa usa de verdad.
- `CPUTime` en `sacct` es lo reservado (duración × núcleos), no lo usado: no
  sirve para medir la eficiencia.
```

### Qué dice el verificador

El perfil (`APOLO_TRAINING_CLUSTER`, o el `cluster` que recibe el `Contexto`)
solo elige el texto del mensaje: nunca cambia si una práctica se aprueba. Los
textos de `apolo3` cubren la VM y Apolo III, porque un usuario `apolo3` usa los
dos.

| Qué ve el verificador                                             | Cuándo pasa                                                                                                   | Perfil `apolo3`                                                        | Perfil `apolo2` o sin perfil                    |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------- |
| `verificar memoria`: terminó bien y nunca hubo `OUT_OF_MEMORY`    | En Apolo III, siempre. En la VM o en Apolo II, si no se envió primero con `--mem=1G` o si el límite se rompió | `memoria_sin_limite_apolo3`: normal en Apolo III; en la VM, `--mem=1G` | `memoria_sin_limite`: avisar al equipo de Apolo |
| `verificar nucleos` o `paralelo`: terminó bien sin CPU registrado | En Apolo III, siempre. En la VM o en Apolo II, solo si el registro de uso se rompió                           | `sin_datos_apolo3`: normal en Apolo III; en la VM, avisar al equipo    | `sin_datos`: avisar al equipo de Apolo          |
| `eficiencia JOBID`: sin CPU ni `MaxRSS`, termine como termine     | Igual que la fila anterior                                                                                    | `efi_sin_datos_apolo3`                                                 | `sin_datos`                                     |
| `eficiencia JOBID`: no llegó a correr o duró menos de 2 s         | En cualquier clúster                                                                                          | `efi_corto`                                                            | `efi_corto`                                     |

- La variable la pone el script de entrada en la VM (P-03) y el modulefile en
  Apolo II y Apolo III (V-06). Mientras la V-06 no la ponga, en Apolo III salen
  los mensajes de `apolo2`.
- El reporte de la V-05 corre como root, con su propio entorno: le pasa al
  `Contexto` el perfil leído de `/etc/apolo-training/usuarios/<usuario>`.

### Cuándo se quita

Si Apolo III empieza a limitar la memoria y los núcleos (`task/cgroup`) y a
registrar el uso (`jobacct_gather`), se repiten las pruebas A, B2 y C de la
A-03 y se quita el aviso de las dos lecciones. El verificador no necesita
cambios: detecta la diferencia por los datos de `sacct`, no por el nombre del
clúster, así que sus mensajes de Apolo III dejan de salir solos.

## Pendientes

| Falta                                                      | Afecta                       | Lo resuelve |
| ---------------------------------------------------------- | ---------------------------- | ----------- |
| Que el Slurm de la VM tenga el plugin `job_submit/lua`     | Partición por defecto (P-02) | Byron       |
| Nombre del módulo de Python con numpy                      | P-04, V-03                   | I-07        |
| Qué límite real recibe un trabajo sin `--time` en Apolo II | `m05/trabajos`               | A-04        |
| Si `/scratch/<usuario>` se crea solo en Apolo III          | `m03/archivos`               | A-04        |

## Aprobación

- [x] Revisado por Juan.
- [x] Revisado por Byron.
