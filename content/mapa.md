# Mapa de contenidos del curso (A-12)

Alcance exacto del curso de inducción: qué enseña cada módulo, en qué
lecciones se divide y qué trae cada lección. Las tareas C-02 a C-11 (texto),
T-03 y T-04 (terminales quemadas), M-02 a M-09 (videos) y el importador (B-04)
parten de aquí. Si algo cambia, se cambia primero en este archivo.

## Resumen

| Módulo                             | Min | Lecciones | Video          | Terminal quemada | Práctica real                        | Preguntas | Quién | Tarea |
| ---------------------------------- | --: | --------: | -------------- | :--------------: | ------------------------------------ | --------: | ----- | ----- |
| 0 · Bienvenida                     |  10 |         3 | —              |        —         | —                                    |         5 | Byron | C-02  |
| 1 · Conexión                       |  25 |         3 | 4 min          |        sí        | SSH a la VM con su propio cliente    |         5 | Byron | C-03  |
| 2 · Terminal y Linux               |  35 |         4 | —              |        sí        | Carpeta del curso y laboratorio      |         8 | Byron | C-04  |
| 3 · Almacenamiento y transferencia |  25 |         3 | —              |        sí        | Subir un archivo con `scp`           |         5 | Byron | C-05  |
| 4 · Software con módulos           |  30 |         3 | 4 min          |        sí        | Laboratorio de módulos ✔             |         5 | Byron | C-06  |
| 5 · Anatomía de un trabajo         |  35 |         3 | 5 min          |        sí        | Laboratorio de memoria ✔             |         6 | Juan  | C-07  |
| 6 · Núcleos y paralelismo          |  35 |         3 | 5 min          |        —         | Laboratorios de núcleos y paralelo ✔ |         6 | Juan  | C-08  |
| 7 · Open OnDemand                  |  25 |         2 | 4 min          |        —         | Graduación en su clúster real ✔      |         4 | Byron | C-09  |
| 8 · VS Code                        |  15 |         1 | —              |        —         | Remote-SSH a la VM (opcional)        |         3 | Byron | C-10  |
| 9 · Cierre y quiz final            |  20 |         2 | —              |        —         | —                                    |        15 | Juan  | C-11  |
| **Total**                          | 255 |        27 | **5 · 22 min** |        5         | 4 laboratorios + graduación          |    **62** |       |       |

✔ = lo revisa el verificador `apolo-training` y aparece en Mi progreso.

- **Videos:** cinco, todos de 5 minutos o menos (22 minutos en total), en
  español con subtítulos en español e inglés. Claves: `m01-conexion`,
  `m04-modulos`, `m05-trabajos`, `m06-paralelismo` y `m07-ondemand`.
- **Laboratorios verificados:** `modulos`, `memoria`, `nucleos` y `paralelo`,
  los mismos identificadores de la API. La graduación se hace en el clúster
  real del usuario.
- **Duración:** unas 4 horas y cuarto con práctica incluida; se puede hacer en
  varias sesiones.

## Reglas para escribir el contenido

- Cada lección sigue la plantilla de la C-01. Una lección puede traer video,
  lectura, terminal quemada, laboratorio y quiz; se completa al cumplir lo que
  trae (ver `docs/diseno/modelo-datos.md`).
- El quiz de cada módulo puede repartirse entre sus lecciones; el total por
  módulo es el de la tabla. Toda pregunta lleva la explicación de la respuesta.
- **Pestañas Apolo II / Apolo III** donde algo cambia. La plataforma abre la del
  clúster del usuario.
- **Siempre `-p <partición>` en los ejemplos de Slurm:** Apolo III no tiene
  partición por defecto y `srun` o `sbatch` sin `-p` fallan (A-03).
- Comandos en bloques `bash` sin el `$`, valores para reemplazar entre
  `<ángulos>`. Cada comando se prueba en la VM de práctica y en el clúster real
  que corresponda, y se anota dónde.
- Texto en español. El inglés llega por los subtítulos; el texto en inglés es de
  la fase 2.
- Sin datos de usuarios reales, IPs ni nombres internos: el repo será público.

## Módulos

Cada lección se identifica como `mNN/slug` (por ejemplo `m05/primer-script`),
que es también su ruta en la plataforma.

### 0 · Bienvenida

**Objetivos.** Al terminar, el usuario:

1. Sabe si su cuenta es de Apolo II o de Apolo III y qué cambia entre los dos.
2. Explica por qué en el login no se corre cómputo y que los núcleo-hora solo
   cuentan mientras el trabajo corre.
3. Conoce el recorrido del curso: VM de práctica, terminales, laboratorios,
   graduación y aprobación.

| Lección             | Título                                     | Trae                 |
| ------------------- | ------------------------------------------ | -------------------- |
| `m00/que-es-apolo`  | Qué es Apolo y cuál es tu clúster          | lectura con pestañas |
| `m00/reglas`        | Reglas de uso: el login no es para cómputo | lectura              |
| `m00/como-funciona` | Cómo funciona este curso                   | lectura, quiz (5)    |

**Quiz (5):** diferencia entre Apolo II y III, qué se hace y qué no en el
login, cuándo se cobran núcleo-hora, qué es la VM de práctica, qué hace falta
para aprobar.

### 1 · Conexión

**Objetivos.**

1. Se conecta a la VPN de EAFIT con GlobalProtect en su sistema operativo.
2. Entra por SSH al login de su clúster y cambia la contraseña temporal en el
   primer ingreso.
3. Se conecta a la VM de práctica con su propio cliente SSH.

| Lección          | Título                        | Trae                                   |
| ---------------- | ----------------------------- | -------------------------------------- |
| `m01/vpn`        | Conéctate a la VPN            | video `m01-conexion`, lectura          |
| `m01/primer-ssh` | Tu primera conexión SSH       | lectura con pestañas, terminal quemada |
| `m01/practica`   | Conéctate a la VM de práctica | práctica real, quiz (5)                |

- **Lectura:** GlobalProtect en Windows, macOS y Linux. Se enlaza la guía
  vigente de apolo-docs (_Configure the VPN_) en vez de copiarla. Hoy no hay
  doble factor en los clústeres (A-08); si se activa, se agrega aquí.
- **Pestañas:** `ssh <usuario>@apolo.eafit.edu.co` (Apolo II) y
  `ssh <usuario>@apolo-3.eafit.edu.co` (Apolo III).
- **Terminal quemada:** `ssh` al login, aceptar la huella del servidor (`yes`),
  contraseña temporal, cambio obligatorio (actual, nueva, repetir), volver a
  entrar, `hostname`, `exit`.
- **Práctica real:** desde su computador y con la VPN,
  `ssh <usuario>@apolo-training.apolo.eafit.edu.co` y cambio de la contraseña
  temporal de la VM. Se aclara que es una contraseña distinta de la de la
  plataforma (`training.apolo.eafit.edu.co`). Las dos solo responden por la
  VPN.
- **Quiz (5):** para qué es la VPN, qué hacer con la huella del servidor, qué
  pasa en el primer ingreso, login real vs VM de práctica, qué contraseña pide
  cada lugar.

### 2 · Terminal y Linux

**Objetivos.**

1. Se mueve por el sistema de archivos con rutas absolutas y relativas.
2. Crea, copia, mueve, borra y edita archivos sin salir de la terminal.
3. Lee los permisos de un archivo y sigue las buenas prácticas del login.

| Lección        | Título                             | Trae                      |
| -------------- | ---------------------------------- | ------------------------- |
| `m02/navegar`  | Moverte por el sistema de archivos | lectura, terminal quemada |
| `m02/archivos` | Crear, copiar, mover y borrar      | lectura, terminal quemada |
| `m02/nano`     | Editar con nano y permisos básicos | lectura, terminal quemada |
| `m02/practica` | Prepara tu carpeta del curso       | práctica real, quiz (8)   |

- **Terminal quemada:** `pwd`, `ls`, `ls -l`, `cd` (con `~` y `..`), `mkdir`,
  `cp`, `cp -r`, `mv`, `rm` (sin papelera), `cat`, `nano` (guardar y salir),
  `chmod +x`.
- **Práctica real:** en la VM, crear `~/curso` y copiar el laboratorio desde la
  carpeta compartida del curso (la ruta la fija la P-04).
- **Quiz (8):** rutas absolutas y relativas, `~` y `..`, `cp` vs `mv`, `rm` no
  tiene papelera, cómo salir de nano, qué significa `rwx`, qué no hacer en el
  login, cómo ver archivos ocultos.

### 3 · Almacenamiento y transferencia

**Objetivos.**

1. Sabe dónde queda su home en su clúster, cuánto cabe y cómo ver lo que ocupa.
2. Sube y baja archivos con `scp` y `rsync`, y sabe cuándo usar cada uno.
3. Sabe qué hacer cuando se llena la cuota.

| Lección          | Título                                  | Trae                      |
| ---------------- | --------------------------------------- | ------------------------- |
| `m03/tu-home`    | Dónde quedan tus archivos y cuánto cabe | lectura con pestañas      |
| `m03/transferir` | Subir y bajar archivos: scp y rsync     | lectura, terminal quemada |
| `m03/practica`   | Sube un archivo a la VM                 | práctica real, quiz (5)   |

- **Pestañas:** Apolo II tiene el home montado por NFS (cuota por confirmar,
  A-04). Apolo III tiene el home en el nodo maestro, con aviso a los 150 GB y
  límite en 200 GB. Las áreas de scratch y compartidas de cada clúster salen de
  la A-04.
- **Terminal quemada:** `du -sh`, `quota -s`, `scp` de ida y de vuelta,
  `rsync -av` (y qué hace la barra final en la ruta de origen).
- **Práctica real:** desde su computador,
  `scp <archivo> <usuario>@apolo-training.apolo.eafit.edu.co:~/curso/`. También se menciona el explorador de archivos de
  OnDemand, que se ve en el módulo 7.
- **Quiz (5):** dónde está el home en su clúster, `scp` vs `rsync`, cómo ver qué
  ocupa más, qué pasa al pasar el límite, qué no guardar en el home.

### 4 · Software con módulos

**Objetivos.**

1. Explica qué es un módulo de Lmod y por qué en Apolo no se instala software
   con `dnf`.
2. Busca, carga y descarga software con `module` en su clúster.
3. Carga el Python con numpy que necesita un trabajo.

| Lección                | Título                                | Trae                                   |
| ---------------------- | ------------------------------------- | -------------------------------------- |
| `m04/que-es-un-modulo` | Qué es un módulo y por qué no hay dnf | video `m04-modulos`, lectura           |
| `m04/cargar`           | Buscar y cargar software              | lectura con pestañas, terminal quemada |
| `m04/laboratorio`      | Laboratorio de módulos                | laboratorio `modulos`, quiz (5)        |

- **Pestañas:** en Apolo III primero va `module use /opt/ohpc/pub/moduledeps/…`.
  Toolchain por defecto: gcc 15.2 con openmpi5-gnu15 en Apolo II, gcc 14.2 con
  openmpi5-gnu14 en Apolo III (se confirma en la A-04).
- **Terminal quemada:** `module avail`, `module spider`, `module use` (solo
  Apolo III), `module load`, `module list`, `module purge`.
- **Laboratorio `modulos`:** el trabajo falla sin numpy y termina al cargar el
  módulo de Python con numpy. El nombre del módulo lo decide la I-07 (propuesta:
  `py3-numpy/1.26.4`, que ya existe con ese nombre en los dos clústeres).
- **Quiz (5):** `avail` vs `spider`, qué hace `module use`, por qué no `dnf`, cómo
  ver lo cargado, cargar módulos dentro del script de Slurm.

### 5 · Anatomía de un trabajo

**Objetivos.**

1. Escribe un script de Slurm con las directivas `#SBATCH` básicas.
2. Envía, vigila y cancela trabajos, y lee su resultado con `sacct`.
3. Elige la partición de su clúster y pide la memoria que el trabajo necesita.

| Lección                   | Título                    | Trae                                                      |
| ------------------------- | ------------------------- | --------------------------------------------------------- |
| `m05/primer-script`       | Tu primer script de Slurm | video `m05-trabajos`, lectura, terminal quemada, quiz (3) |
| `m05/particiones`         | Particiones de tu clúster | lectura con pestañas, quiz (3)                            |
| `m05/laboratorio-memoria` | Laboratorio de memoria    | laboratorio `memoria`, terminal real                      |

- **Pestañas:** Apolo II tiene `longjobs` por defecto (14 días), `bigmem`,
  `accel`, `accel-2` y `learning`. Apolo III tiene `bigmem` (4 días),
  `longjobs` (6 días) y `accel` (3 días), y no tiene partición por defecto. La
  pestaña de Apolo III lleva el aviso de la P-05: hoy no limita la memoria ni
  registra el uso de CPU.
- **Terminal quemada (T-04):** `sbatch`, `squeue` (estados PD, R y CD, razones
  `Priority` y `Resources`), `scancel` y `sacct -X -o JobID,State,Elapsed,MaxRSS`,
  con salidas realistas de cada clúster.
- **Laboratorio `memoria`:** el trabajo pide `--mem=1G`, termina en
  `OUT_OF_MEMORY`, el usuario lo ve con `sacct`, sube a `--mem=4G` y termina
  bien. El verificador lo da por aprobado.
- **Quiz (6):** directivas básicas, qué significa PD y su razón, cómo cancelar,
  por qué falló por memoria, por qué siempre `-p` en Apolo III, qué hace
  `--time`.

### 6 · Núcleos y paralelismo

**Objetivos.**

1. Distingue entre los núcleos reservados y los que el programa usa de verdad.
2. Mide la eficiencia de un trabajo con `apolo-training eficiencia JOBID`.
3. Ajusta `--cpus-per-task` y `--ntasks` para que un programa paralelo use lo
   que reserva.

| Lección                    | Título                                     | Trae                                            |
| -------------------------- | ------------------------------------------ | ----------------------------------------------- |
| `m06/reservados-y-usados`  | Núcleos reservados frente a núcleos usados | video `m06-paralelismo`, lectura, quiz (3)      |
| `m06/laboratorio-nucleos`  | Laboratorio de núcleos                     | laboratorio `nucleos`, terminal real            |
| `m06/laboratorio-paralelo` | Laboratorio de paralelo                    | laboratorio `paralelo`, terminal real, quiz (3) |

- **Sin terminal quemada:** aquí la práctica es real, porque lo que se mide es el
  uso verdadero de CPU.
- **Laboratorio `nucleos`:** el mismo cálculo con 1 y con varios núcleos
  reservados; el usuario compara tiempos y eficiencia. El laboratorio dura de 30
  a 60 s con los 4 núcleos de la VM (se calibra en la V-03).
- **Laboratorio `paralelo`:** un trabajo que reserva varios núcleos pero no los
  usa, y su corrección.
- Estas dos descripciones hay que confirmarlas con el código vigente de los
  laboratorios (`pi.py`, `curso.sh`) cuando entre a `labs/`.
- **Pestaña de Apolo III:** aviso de la P-05; allí `TotalCPU` sale vacío, así que
  la eficiencia solo se puede medir en la VM o en Apolo II.
- **Quiz (6):** reservar vs usar, qué mide la eficiencia, `--cpus-per-task` vs
  `--ntasks`, cuándo pedir más núcleos no ayuda, cómo se cobran los núcleo-hora,
  qué hacer con una eficiencia baja.

### 7 · Open OnDemand

**Objetivos.**

1. Usa OnDemand para manejar archivos y abrir aplicaciones interactivas.
2. Explica por qué cerrar la pestaña del navegador no libera los recursos y cómo
   cerrar bien una sesión.
3. Hace la graduación en su clúster real y la envía desde Mi progreso.

| Lección          | Título                              | Trae                                       |
| ---------------- | ----------------------------------- | ------------------------------------------ |
| `m07/ondemand`   | Archivos y aplicaciones en OnDemand | video `m07-ondemand`, lectura con pestañas |
| `m07/graduacion` | Tu graduación en el clúster real    | práctica real (graduación), quiz (4)       |

- **Pestañas:** el OnDemand que atiende a cada clúster (A-04).
- **Graduación (V-07):** con la VPN, abrir una sesión interactiva de OnDemand en
  su clúster, cerrarla desde _My Interactive Sessions_, entrar por SSH al login,
  correr `module load apolo-training` y
  `apolo-training verificar ondemand JOBID`, y pegar el JobID y la salida en Mi
  progreso.
- **Quiz (4):** qué pasa al cerrar la pestaña, dónde se cierra una sesión, qué
  cuenta como graduación, a quién llega lo que envía.

### 8 · VS Code

**Objetivos.**

1. Abre una carpeta remota con la extensión Remote-SSH de VS Code.
2. Explica que VS Code sirve para editar y que el cómputo va siempre por Slurm.
3. Sabe cerrar la conexión para no dejar procesos en el login.

| Lección          | Título                        | Trae                                      |
| ---------------- | ----------------------------- | ----------------------------------------- |
| `m08/remote-ssh` | Editar con VS Code Remote-SSH | lectura, práctica real opcional, quiz (3) |

- **Práctica opcional:** Remote-SSH a `apolo-training.apolo.eafit.edu.co`.
- **Quiz (3):** dónde corre el servidor de VS Code, por qué no correr el programa
  desde la terminal de VS Code en el login, cómo cerrar la sesión remota.

### 9 · Cierre y quiz final

**Objetivos.**

1. Pide ayuda con la información que el equipo necesita (siempre el JobID).
2. Sabe dónde está la documentación y a dónde escribir.
3. Demuestra lo aprendido en el quiz final.

| Lección           | Título           | Trae            |
| ----------------- | ---------------- | --------------- |
| `m09/pedir-ayuda` | Cómo pedir ayuda | lectura         |
| `m09/quiz-final`  | Quiz final       | quiz final (15) |

- **Pedir ayuda:** correo `apolo@eafit.edu.co` con clúster, usuario, JobID,
  comando, salida de error y qué se esperaba. Documentación en
  <https://apolo-docs.readthedocs.io>.
- **Qué sigue:** con todo aprobado, el equipo aplica la QOS normal en su clúster
  real.
- **Quiz final (15):** de 1 a 2 preguntas de cada módulo del 1 al 8; apruebas con
  80 % (12 de 15).

## Pendientes que afectan este mapa

| Pendiente                                                 | Afecta                    | Lo resuelve |
| --------------------------------------------------------- | ------------------------- | ----------- |
| Ruta de la carpeta compartida del laboratorio             | módulo 2                  | P-04, V-04  |
| Cuota del home de Apolo II, scratch y áreas compartidas   | módulo 3                  | A-04        |
| Toolchain por defecto confirmado                          | módulo 4                  | A-04, I-06  |
| Nombre del módulo de Python con numpy                     | módulo 4 y laboratorios   | I-07        |
| `longjobs-smt` y `learning`: quién las ve y si se enseñan | módulo 5                  | P-01, P-02  |
| Qué OnDemand atiende a cada clúster                       | módulo 7                  | A-04        |
| Las 10 preguntas más repetidas en soporte                 | quizzes y «Si algo falla» | A-10        |

## Aprobación

- [ ] Revisado por Juan (módulos 0 a 4, 7 y 8).
- [ ] Revisado por Byron (módulos 5, 6 y 9).
- [ ] Aprobado por la coordinación (comentario en el PR o correo).
