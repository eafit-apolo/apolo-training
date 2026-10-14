# Glosario ES → EN

Traducción fija de los términos del curso, para que los subtítulos en inglés,
la interfaz y la versión en inglés del contenido usen siempre la misma palabra.

- Si un término no está, se agrega aquí en el mismo PR que lo usa por primera
  vez.
- En español se usa siempre la palabra de la primera columna, aunque haya
  sinónimos (por ejemplo, «trabajo» y no «job» ni «tarea»).

## Clústeres y Slurm

| Español               | Inglés              | Nota                                                                        |
| --------------------- | ------------------- | --------------------------------------------------------------------------- |
| clúster               | cluster             | Con tilde en español. Apolo II y Apolo III no se traducen.                  |
| nodo                  | node                |                                                                             |
| nodo de login         | login node          | No «nodo de inicio de sesión». No es para cómputo.                          |
| nodo de cómputo       | compute node        |                                                                             |
| trabajo               | job                 | No «tarea»: en Slurm, _task_ es otra cosa (`--ntasks`).                     |
| script del trabajo    | job script          | El archivo con las directivas `#SBATCH`.                                    |
| directiva             | directive           | Cada línea `#SBATCH`.                                                       |
| enviar (un trabajo)   | submit (a job)      | No «lanzar» ni «someter».                                                   |
| cancelar (un trabajo) | cancel (a job)      |                                                                             |
| cola                  | queue               |                                                                             |
| partición             | partition           |                                                                             |
| partición por defecto | default partition   |                                                                             |
| estado                | state               | Los estados (`PD`, `R`, `CD`…) no se traducen.                              |
| en espera             | pending             | El estado `PD`.                                                             |
| en ejecución          | running             | El estado `R`.                                                              |
| terminado             | completed           | El estado `CD`.                                                             |
| razón de espera       | pending reason      | La última columna de `squeue`.                                              |
| núcleo                | core                | No «CPU» en el texto, salvo en el nombre de una opción (`--cpus-per-task`). |
| memoria               | memory              |                                                                             |
| reservar (recursos)   | request (resources) | Lo que se pide con `#SBATCH`.                                               |
| eficiencia            | efficiency          | Lo que muestra `apolo-training eficiencia`.                                 |
| límite de tiempo      | time limit          | `--time`.                                                                   |
| sesión interactiva    | interactive session |                                                                             |

## Software y archivos

| Español                 | Inglés               | Nota                                                                |
| ----------------------- | -------------------- | ------------------------------------------------------------------- |
| módulo (de software)    | module               | El de Lmod. No confundir con «módulo del curso».                    |
| cargar (un módulo)      | load (a module)      |                                                                     |
| terminal                | terminal             |                                                                     |
| carpeta                 | folder               | No «directorio» en el texto.                                        |
| carpeta personal (home) | home folder          | En español se escribe «home» solo cuando se habla de la ruta (`~`). |
| ruta                    | path                 |                                                                     |
| archivo                 | file                 |                                                                     |
| cuota                   | quota                |                                                                     |
| subir / descargar       | upload / download    | Desde el punto de vista del computador del usuario.                 |
| contraseña              | password             |                                                                     |
| huella del servidor     | host key fingerprint | Lo que pide aceptar `ssh` la primera vez.                           |

## Curso y plataforma

| Español            | Inglés            | Nota                                                                                   |
| ------------------ | ----------------- | -------------------------------------------------------------------------------------- |
| curso de inducción | onboarding course |                                                                                        |
| módulo (del curso) | module            |                                                                                        |
| lección            | lesson            |                                                                                        |
| práctica           | practice          | Cualquier ejercicio en la VM que revisa `apolo-training verificar`.                    |
| laboratorio        | lab               | Solo las prácticas con trabajos de Slurm: `modulos`, `memoria`, `nucleos`, `paralelo`. |
| VM de práctica     | practice VM       | `apolo-training.apolo.eafit.edu.co`.                                                   |
| verificador        | checker           | El comando `apolo-training`.                                                           |
| verificar          | check             |                                                                                        |
| graduación         | graduation        | El trabajo final en el clúster real.                                                   |
| quiz               | quiz              | Plural en español: «quices».                                                           |
| Mi progreso        | My progress       | Nombre de la pantalla.                                                                 |

## No se traduce

- Nombres de comandos, opciones y archivos: `sbatch`, `squeue`, `sacct`,
  `scancel`, `module`, `ssh`, `scp`, `rsync`, `nano`, `--mem`, `curso.sh`…
- Estados de Slurm: `PD`, `R`, `CD`, `OUT_OF_MEMORY`, `COMPLETED`…
- Nombres propios: Slurm, Lmod, Apolo II, Apolo III, GlobalProtect, OnDemand,
  VS Code.
- JobID.
- Los nombres de las prácticas (`conexion`, `terminal`, `archivos`…), porque
  son argumentos del verificador.
