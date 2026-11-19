# Mapa de contenidos del curso (A-12)

Alcance exacto del curso de inducción: qué enseña cada módulo, qué video lo
explica, qué práctica hace el usuario y qué preguntas responde. Las tareas de
contenido (C-xx), videos (M-xx) y el importador (B-04) parten de aquí. Si algo
cambia, se cambia primero en este archivo.

## Cómo es el curso

- **Dura entre 60 y 90 minutos en total**, contando videos, quices y práctica.
  Es lo que toma hoy una inducción presencial; más largo, la gente no lo
  termina.
- **Cada módulo es: video corto + quiz de 1 o 2 preguntas + práctica.** El
  video explica; debajo va un resumen con los comandos para copiarlos y
  consultarlos después, no una lectura larga.
- **La práctica es real, en la VM de práctica**
  (`apolo-training.apolo.eafit.edu.co`). El usuario escribe los comandos de
  verdad, desde la terminal de la plataforma o con su propio cliente SSH. No hay
  terminales simuladas: la VM es un entorno seguro, donde un error solo afecta
  al propio usuario. La excepción es conda (módulo 8), que se practica en su
  clúster real.
- **La graduación es en su clúster real** (Apolo II o Apolo III), con un
  trabajo corto por lotes que el verificador revisa ahí mismo.
- **La VPN llega resuelta.** El curso no tiene lección de VPN: la plataforma
  solo carga con la VPN encendida, así que el correo de bienvenida trae el
  enlace a la guía de apolo-docs (A-17).

## Resumen

| Módulo                       | Videos                                     | Práctica                                                | Preguntas |    Min | Quién |
| ---------------------------- | ------------------------------------------ | ------------------------------------------------------- | --------: | -----: | ----- |
| 0 · Bienvenida               | Bienvenida (3 min)                         | —                                                       |         2 |      4 | Byron |
| 1 · Conexión                 | SSH (3 min)                                | Conectarse con su cliente SSH y cambiar la contraseña ✔ |         2 |      9 | Byron |
| 2 · Terminal y Linux         | Terminal y Linux (4 min)                   | Preparar el material y encontrar la clave con grep ✔    |         2 |     10 | Juan  |
| 3 · Archivos y transferencia | Archivos (3 min)                           | Bajar `ida.txt` y subirlo como `vuelta.txt` ✔           |         2 |      8 | Juan  |
| 4 · Software con módulos     | Módulos (3 min)                            | Laboratorio de módulos ✔                                |         2 |      9 | Byron |
| 5 · Trabajos con Slurm       | Trabajos (5 min)                           | Laboratorio de memoria ✔ y estados de la cola           |         2 |     13 | Juan  |
| 6 · Núcleos y paralelismo    | Paralelismo (4 min)                        | Laboratorios de núcleos y paralelo ✔                    |         2 |     14 | Juan  |
| 7 · VS Code y graduación     | VS Code (2 min)                            | Graduación en su clúster real ✔ (VS Code opcional)      |         2 |      9 | Juan  |
| 8 · Ambientes de conda       | Conda (4 min)                              | Crear un ambiente y usarlo en un trabajo, en su clúster |         2 |      9 | Byron |
| 9 · Cierre                   | —                                          | —                                                       | 9 (final) |      5 | Juan  |
| **Total**                    | **9 por grabar; cada usuario ve ≈ 31 min** | **7 prácticas verificadas + graduación**                |    **27** | **90** |       |

✔ = lo revisa el verificador `apolo-training` y aparece en Mi progreso.

- **Videos por grabar (9):** bienvenida, SSH, terminal y Linux, archivos,
  módulos, trabajos, paralelismo, VS Code y conda. Todos los usuarios ven los
  nueve. Cada uno de 5 minutos o menos, en español con subtítulos en español e
  inglés, y grabado a partir de un guion en `content/guiones/` (M-02 y M-09).
- **Las prácticas de la VM se verifican igual:** cada una termina con
  `apolo-training verificar <práctica>` en la VM y su resultado llega a Mi
  progreso. Son siete: `conexion`, `terminal`, `archivos`, `modulos`,
  `memoria`, `nucleos` y `paralelo`. La graduación se verifica igual, con
  `apolo-training verificar graduacion JOBID` en el clúster real. La práctica
  de conda no se verifica.
- **Quién:** responde por el video, el resumen y el quiz del módulo. Byron
  graba 4 videos (unos 13 min) y Juan 5 (unos 18 min); ver «Reparto de videos».
- **Minutos por módulo:** video + práctica + quiz (unos 30 segundos por
  pregunta). La práctica opcional de VS Code no cuenta. Con conda, el curso
  queda en el tope de 90 minutos: un video más largo obliga a recortar otro.

## Reglas para el contenido

- **Video primero.** Lo que haga falta explicar va en el video. Debajo, un
  resumen corto con los comandos del video, en bloques `bash` sin el `$` y con
  los valores para reemplazar entre `<ángulos>`.
- **Pestañas Apolo II / Apolo III** en el resumen donde algo cambia. La
  plataforma abre la del clúster del usuario.
- **Siempre con partición en Slurm:** en el script, con
  `#SBATCH --partition=<partición>`, y se envía con `sbatch <script>.sh`. `-p`
  queda para enviar a otra partición sin editar el script, para `--wrap` y para
  la graduación (el mismo `graduacion.sh` en los dos clústeres). Apolo III no
  tiene partición por defecto y un trabajo sin partición falla (A-03; decidido
  el 19-nov en la C-07).
- **Quiz corto:** 1 o 2 preguntas por módulo, que se respondan en menos de 30
  segundos cada una, con la explicación de la respuesta.
- **Práctica con instrucciones numeradas** y un resultado que el usuario pueda
  comprobar. Cada comando se prueba en la VM y en el clúster real que
  corresponda.
- Sin datos de usuarios reales, IPs ni nombres internos: el repo será público.

## Módulos

Cada lección se identifica como `mNN/slug`, que es también su ruta en la
plataforma.

### 0 · Bienvenida · 4 min

| Lección          | Trae                             |
| ---------------- | -------------------------------- |
| `m00/bienvenida` | video (3 min), resumen, quiz (2) |

- **Video:** una bienvenida general, para alguien que nunca ha usado un clúster.
  Qué es Apolo y para qué le sirve; la idea de clúster compartido, donde los
  cálculos esperan turno en una cola; que tiene una cuenta en Apolo II o en
  Apolo III y la plataforma le muestra lo de su clúster; y cómo funciona el
  curso: módulos, VM de práctica, graduación y qué hace falta para aprobar. No
  trae comandos, direcciones ni pasos para conectarse: eso empieza en el
  módulo 1.
- **Quiz (2):** por qué los cálculos esperan turno en un clúster compartido;
  qué hace falta para aprobar.

### 1 · Conexión · 9 min

| Lección   | Trae                                           |
| --------- | ---------------------------------------------- |
| `m01/ssh` | video SSH (3 min), práctica en la VM, quiz (2) |

- **Sin lección de VPN** (12-nov): la plataforma solo carga con la VPN
  encendida, así que no tiene sentido enseñarla ahí. El correo de bienvenida
  trae el enlace vigente a la guía de apolo-docs (A-17).
- **Video SSH:** abrir una terminal en su sistema operativo, conectarse al
  login (`apolo.eafit.edu.co` o `apolo-3.eafit.edu.co`), la huella del
  servidor, el cambio de contraseña en el primer ingreso y qué contraseña pide
  cada lugar.
- **Práctica:**
  1. Con la VPN encendida, `ssh <usuario>@apolo-training.apolo.eafit.edu.co`.
  2. Aceptar la huella y cambiar la contraseña temporal.
  3. Volver a entrar con la nueva y correr `hostname`.
  4. `apolo-training verificar conexion`.

  Se aclara que es la contraseña de la VM, distinta de la de la plataforma.

- **Quiz (2):** para qué es la VPN; qué contraseña pide cada lugar.

### 2 · Terminal y Linux · 10 min

| Lección        | Trae                                                |
| -------------- | --------------------------------------------------- |
| `m02/terminal` | video (4 min), resumen, práctica en la VM, quiz (2) |

- **Video:** `pwd`, `ls`, `ls -l`, `cd` (con `~` y `..`), `mkdir`, `cp`,
  `cp -r`, `mv`, `rm` (no hay papelera), `cat`, `grep` (y `grep -r` para buscar
  en una carpeta), `nano` (guardar y salir) y `>` para guardar en un archivo lo
  que imprime un comando. Los permisos solo se leen con `ls -l`; no se enseña
  `chmod`: los scripts de Slurm no lo necesitan y mal usado deja los archivos
  expuestos a otros usuarios.
- **Práctica** (`labs/terminal/LEEME.txt`):
  1. `apolo-training preparar`: copia el material del curso a
     `~/apolo-training`. Se corre una sola vez y deja lista también la práctica
     del módulo 3.
  2. `cd ~/apolo-training/terminal` y leer `LEEME.txt` con `cat`.
  3. Recorrer `datos/` con `cd`, `ls` y `cat`. En uno de los archivos hay una
     línea con la clave del curso, que empieza por `TRN-`; `grep -r TRN- datos/`
     la encuentra sin abrir archivo por archivo.
  4. Guardar la clave en `respuesta.txt`, con `nano` o con
     `echo <clave> > respuesta.txt`.
  5. `apolo-training verificar terminal`.
- **Quiz (2):** qué hace `rm` (no hay papelera); cómo salir de nano guardando.

### 3 · Archivos y transferencia · 8 min

| Lección        | Trae                                                             |
| -------------- | ---------------------------------------------------------------- |
| `m03/archivos` | video (3 min), resumen con pestañas, práctica en la VM, quiz (2) |

- **Video:** dónde está el home en cada clúster y cuánto cabe, `du -sh`,
  `quota -s`, `scp` para archivos sueltos, `rsync -av` para carpetas grandes
  (no se enseña `--delete`) y FileZilla para quien prefiera arrastrar archivos
  (protocolo SFTP, puerto 22, con la VPN encendida). Se elige FileZilla porque
  es el que existe para Windows, macOS y Linux; en Windows se baja de la página
  oficial y se rechazan las ofertas de otros programas si el instalador las
  muestra.
- **Pestañas del resumen:** Apolo II, home por NFS con cuota por grupo
  (habitual: aviso a los 180 GB y límite en 200 GB); Apolo III, home en el nodo
  maestro con cuota por usuario (aviso a los 150 GB, límite en 200 GB y 7 días
  de gracia). Datos de la A-04.
- **Práctica** (`labs/archivos/LEEME.txt`): una ida y vuelta con un archivo que
  tiene un código propio de cada usuario.
  1. En la VM, `ls ~/apolo-training/archivos`: ahí está `ida.txt` (lo generó
     `apolo-training preparar` en el módulo 2).
  2. Desde su computador, descargarlo:
     `scp <usuario>@apolo-training.apolo.eafit.edu.co:apolo-training/archivos/ida.txt .`
  3. Cambiarle el nombre: `mv ida.txt vuelta.txt` (sirve igual en Linux, macOS
     y PowerShell).
  4. Subirlo:
     `scp vuelta.txt <usuario>@apolo-training.apolo.eafit.edu.co:apolo-training/archivos/`
  5. En la VM, `du -sh ~/apolo-training` para ver cuánto ocupa.
  6. `apolo-training verificar archivos`.

  Los pasos 2 a 4 también se pueden hacer con FileZilla: el verificador solo
  revisa que `vuelta.txt` tenga el código de `ida.txt`.

- **Quiz (2):** `scp` frente a `rsync`; qué pasa al pasar el límite de la cuota.

### 4 · Software con módulos · 9 min

| Lección       | Trae                                                                 |
| ------------- | -------------------------------------------------------------------- |
| `m04/modulos` | video (3 min), resumen con pestañas, laboratorio `modulos`, quiz (2) |

- **Video:** qué es un módulo y por qué no se instala con `dnf`;
  `module avail`, `module spider` (busca en todo el árbol y dice qué cargar
  antes), `module load`, `module list` y `module purge`.
- **Pestañas del resumen:** en Apolo III primero va
  `module use /opt/ohpc/pub/moduledeps/…`. Toolchain: gcc 15.2 en Apolo II,
  gcc 14.2 en Apolo III (A-04). En la VM todos tienen `gnu14` (I-06): la
  pestaña Apolo II aclara que en su clúster verá `gnu15`.
- **Laboratorio `modulos`:** el trabajo falla sin numpy, el usuario busca el
  módulo con `module spider`, lo carga en el script y el trabajo termina. Cierra con
  `apolo-training verificar modulos`. Nombre
  del módulo: I-07 (propuesta `py3-numpy/1.26.4`).
- **Quiz (2):** `avail` frente a `spider`; dónde se carga el módulo para que
  funcione en el trabajo.

### 5 · Trabajos con Slurm · 13 min

| Lección        | Trae                                                                 |
| -------------- | -------------------------------------------------------------------- |
| `m05/trabajos` | video (5 min), resumen con pestañas, laboratorio `memoria`, quiz (2) |

- **Video:** directivas `#SBATCH`, particiones de cada clúster, `sbatch`,
  `squeue` (estados PD, R y CD y la razón de espera), `scancel` y `sacct`.
- **Pestañas del resumen:** Apolo II tiene `longjobs` por defecto (14 días),
  `bigmem`, `accel`, `accel-2` y `learning`. Apolo III tiene `bigmem` (4 días),
  `longjobs` (6 días) y `accel` (3 días), sin partición por defecto, con el
  aviso de la P-05.
- **Laboratorio `memoria`:**
  1. Enviar el trabajo con `--mem=1G`.
  2. Ver con `sacct` que terminó en `OUT_OF_MEMORY`.
  3. Subir a `--mem=4G` y reenviarlo hasta que termine bien.
  4. `apolo-training verificar memoria`.
- **Estados de la cola, en vivo:** el usuario envía tres copias de un trabajo
  corto; como la QOS del curso permite dos a la vez (I-08), ve la tercera en
  `PD` con su razón en `squeue` y la cancela con `scancel`.
- **Quiz (2):** qué significa `PD` y dónde se ve la razón; por qué falló por
  memoria.

### 6 · Núcleos y paralelismo · 14 min

| Lección           | Trae                                                         |
| ----------------- | ------------------------------------------------------------ |
| `m06/paralelismo` | video (4 min), laboratorios `nucleos` y `paralelo`, quiz (2) |

- **Video:** núcleos reservados frente a núcleos usados, `--cpus-per-task`
  frente a `--ntasks`, `apolo-training eficiencia JOBID` y por qué reservar de
  más perjudica a los demás. Aviso de la P-05 para Apolo III.
- **Laboratorio `nucleos`:** el mismo cálculo con 1 y con varios núcleos; el
  usuario compara tiempo y eficiencia (30 a 60 s con los 4 núcleos de la VM,
  V-03).
- **Laboratorio `paralelo`:** un trabajo que reserva núcleos que no usa, y su
  corrección.
- Cada uno cierra con `apolo-training verificar nucleos` y
  `apolo-training verificar paralelo`.
- Las dos descripciones se confirman con el código de los laboratorios
  (`pi.py`, `curso.sh`) cuando entre a `labs/`.
- **Quiz (2):** qué mide la eficiencia; qué hacer si sale baja.

### 7 · VS Code y graduación · 9 min

| Lección          | Trae                                                          |
| ---------------- | ------------------------------------------------------------- |
| `m07/vscode`     | video (2 min), aviso de OnDemand, práctica opcional, quiz (2) |
| `m07/graduacion` | graduación en su clúster real                                 |

- **Video de VS Code:** Remote-SSH para editar; el cómputo va por Slurm, nunca
  en el login; cerrar la conexión al terminar.
- **Práctica opcional:** Remote-SSH a `apolo-training.apolo.eafit.edu.co`.
- **Aviso de OnDemand** (texto, sin video): Apolo III tiene además una interfaz
  web, OnDemand, que este curso no cubre. Quien la use debe saber que cerrar la
  pestaña no libera los recursos: la sesión se termina en
  _My Interactive Sessions_. Enlace a su guía en apolo-docs.
- **Graduación (V-07):** el primer trabajo en su clúster real, con lo aprendido
  en los módulos 4 a 6. Es corto (1 o 2 núcleos, menos de un minuto) y pide
  `--mem=1G`, para no apartar memoria que no usa.
  1. Con la VPN, por SSH al login de su clúster.
  2. `module load apolo-training` y `apolo-training preparar`.
  3. Enviar el trabajo de graduación (`graduacion.sh`) con la partición de su
     clúster, en pestañas: Apolo II, `sbatch -p learning graduacion.sh`;
     Apolo III, `sbatch -p bigmem graduacion.sh`. Slurm escoge el nodo; no se
     fija ninguno.
  4. Seguirlo con `squeue -u $USER` y, al terminar, ver su estado con
     `sacct -j JOBID`.
  5. `apolo-training verificar graduacion JOBID`.
  6. Enviar el JobID y la salida desde Mi progreso; un instructor la revisa.
- **Qué revisa el verificador** (detalle en la V-07): que el trabajo sea del
  usuario, se llame `curso-graduacion`, haya corrido en la partición del curso
  de ese clúster y terminara en `COMPLETED`. No mide eficiencia, porque Apolo
  III no registra el uso real de CPU.
- **Quiz (2):** para qué sí y para qué no sirve VS Code en el login; qué hacer
  con la conexión de VS Code al terminar.

### 8 · Ambientes de conda · 9 min

| Lección     | Trae                                                                  |
| ----------- | --------------------------------------------------------------------- |
| `m08/conda` | video (4 min), resumen con pestañas, práctica en su clúster, quiz (2) |

- **Video:** qué es conda y para qué sirve (instalar software propio sin pedir
  permisos), cargar `miniconda3`, crear un ambiente con conda-forge, activarlo,
  instalar en él y usarlo dentro de un trabajo de Slurm; `conda clean --all` y
  cuánto pesan los ambientes frente a la cuota del home. Responde lo que se
  repite en cada inducción: si su software es compatible con conda, úselo sin
  miedo.
- **Pestañas del resumen:** versión de `miniconda3` de cada clúster
  (25.11.1 en Apolo II; 25.5.1 por defecto en Apolo III, A-04) y la partición
  del trabajo de ejemplo (siempre con `-p`).
- **Práctica en su clúster real**, sin `apolo-training verificar`: crear un
  ambiente, instalar un paquete y usarlo en un trabajo corto. Los comandos se
  prueban en Apolo II y en Apolo III (C-14).
- **Quiz (2):** dónde se activa el ambiente para que funcione en el trabajo;
  qué hacer cuando los ambientes llenan la cuota.

### 9 · Cierre · 5 min

| Lección      | Trae                                        |
| ------------ | ------------------------------------------- |
| `m09/cierre` | resumen de cómo pedir ayuda, quiz final (9) |

- **Pedir ayuda:** correo `apolo@eafit.edu.co` con clúster, usuario, JobID,
  comando, salida del error y qué se esperaba. Documentación en
  <https://apolo-docs.readthedocs.io>.
- **Qué sigue:** con todo aprobado, el equipo aplica la QOS normal en su clúster
  real.
- **Quiz final (9):** una pregunta de cada módulo del 1 al 8 (la de conda la
  pasa la C-14), más una de integración; se aprueba con 80 % (8 de 9).

## Reparto de videos

| Quién | Videos                                                                         | Cantidad | Minutos |
| ----- | ------------------------------------------------------------------------------ | -------: | ------: |
| Byron | Bienvenida (3), SSH (3), módulos (3), conda (4)                                |        4 |    ≈ 13 |
| Juan  | Terminal y Linux (4), archivos (3), trabajos (5), paralelismo (4), VS Code (2) |        5 |    ≈ 18 |

Cada video se graba a partir de un guion de dos columnas (qué se dice y qué se
muestra) en `content/guiones/`: los de Byron en la M-02 y los de Juan en la
M-09. El otro lo revisa antes de grabar.

## Pendientes que afectan este mapa

| Pendiente                                                                               | Afecta           | Lo resuelve |
| --------------------------------------------------------------------------------------- | ---------------- | ----------- |
| Instalar `apolo-training` en la 116 y en Apolo II y Apolo III, visible sin `module use` | módulos 2, 3 y 7 | V-06, V-07  |
| Scratch y áreas compartidas de cada clúster                                             | módulo 3         | A-04        |
| Nombre del módulo de Python con numpy                                                   | módulos 4 a 7    | I-07        |
| Enlace a la guía de OnDemand en apolo-docs                                              | módulo 7         | C-09        |
| Enlace vigente a la guía de la VPN en el correo de bienvenida                           | módulo 1         | A-17        |
| Versión de `miniconda3` y comandos de conda probados en Apolo II y Apolo III            | módulo 8         | C-14        |
| Las 10 preguntas más repetidas en soporte                                               | quices           | A-10        |

## Cambios que este mapa pidió al plan (A-12)

Se aplicaron a las tarjetas el 9-oct, al fusionar el PR #3.

| Tareas                 | Cambio                                                                                                                                                                                       |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-01, T-02, T-03, T-04 | Se eliminan: no hay terminales quemadas (libera unas 42 h: 30 de Juan y 12 de Byron).                                                                                                        |
| H-04 (go/no-go)        | «Terminal quemada» pasa a «práctica en la VM». La terminal real de la plataforma (T-06) cae después del 19-nov, así que el criterio se cumple con el cliente SSH del usuario.                |
| M-xx                   | De 5 videos a 11 por grabar, más el de Sofía; reparto parejo: Byron 6 (≈ 16 min) y Juan 5 (≈ 18 min). Hay que recalcular horas.                                                              |
| C-02 a C-11            | El texto se reduce a resúmenes bajo cada video. Responsables: Byron los módulos 0, 1 y 4; Juan los módulos 2, 3, 5, 6, 7 y 8. C-09 y C-10 se unen (módulo 7); C-11 pasa al módulo 8.         |
| V-01, V-03             | El verificador suma tres prácticas: `conexion`, `terminal` y `archivos` (siete en total).                                                                                                    |
| A-11 (diseño)          | Quitar la terminal quemada (`escenario`, `POST /api/progreso/terminal`), sumar `conexion`, `terminal` y `archivos` a `LabId` y permitir un video por sistema operativo en la lección de VPN. |

## Cambios del 15-oct: OnDemand sale del curso

OnDemand solo existe en Apolo III, así que no puede ser la graduación de todos.
El módulo 7 pasa a VS Code con un aviso de OnDemand, la graduación pasa a un
trabajo por lotes en el clúster real, y las prácticas de los módulos 2 y 3 se
describen como quedaron en la V-01. Se aplican a las tarjetas cuando se apruebe
este PR.

| Tareas                                   | Cambio                                                                                                                                                                                 |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C-09                                     | Módulo 7 = VS Code, aviso de OnDemand y graduación (`m07/vscode` y `m07/graduacion`).                                                                                                  |
| M-05                                     | Se elimina: ya no se usa el video de OnDemand de Sofía.                                                                                                                                |
| Video de archivos (M-xx de Juan)         | Incluye FileZilla (SFTP, puerto 22).                                                                                                                                                   |
| V-07                                     | `graduacion.sh` (`curso-graduacion`, 1 o 2 núcleos, `--mem=1G`), `-p learning` en Apolo II y `-p bigmem` en Apolo III, y `apolo-training verificar graduacion JOBID`.                  |
| V-06 / V-07                              | Instalar `apolo-training` también en Apolo II y Apolo III, con el modulefile visible sin `module use` (aprobado por la coordinación el 15-oct).                                        |
| P-01                                     | `docs/perfiles.md` deja la partición de la graduación de cada clúster.                                                                                                                 |
| H-07                                     | Quitar OnDemand de lo que revisa.                                                                                                                                                      |
| A-11 (diseño)                            | Quitar OnDemand de `docs/diseno/modelo-datos.md` (graduaciones y el video `m07-ondemand`); va en el PR de ajuste del diseño.                                                           |
| B-02, B-07, F-07, F-08, V-08, P-06, V-09 | La graduación guarda el JobID de un trabajo por lotes y la salida del verificador, no una sesión de OnDemand. En principio solo cambia qué se verifica; revisar cada una al aplicarlo. |

## Cambios del 12-nov: sale la VPN y entra conda

La plataforma solo carga con la VPN encendida, así que enseñarla dentro del
curso no tiene sentido: el enlace a la guía va en el correo de bienvenida. En
su lugar entra un módulo de ambientes de conda, que es lo que más se pregunta
en cada inducción. La bienvenida pasa a ser general, sin pasos para
conectarse. Decisión de Juan, hablada con la coordinación.

| Tareas        | Cambio                                                                                                    |
| ------------- | --------------------------------------------------------------------------------------------------------- |
| A-17          | Nueva: el correo de bienvenida lleva el enlace vigente a la guía de la VPN de apolo-docs.                 |
| C-03          | Módulo 1 sin la lección `m01/vpn`: solo `m01/ssh`.                                                        |
| C-14          | Nueva: módulo 8, ambientes de conda (`m08/conda`), con práctica en el clúster real.                       |
| C-11          | El cierre pasa al módulo 9 (`m09/cierre`) y el quiz final a 9 preguntas, con una de conda.                |
| C-02          | La bienvenida no trae comandos ni direcciones para conectarse.                                            |
| M-02, M-03    | Byron graba 4 videos: bienvenida, SSH, módulos y conda. Salen los tres de VPN.                            |
| M-09, M-04    | Sin cambios: Juan graba 5.                                                                                |
| A-11 (diseño) | Ya no hace falta un video por sistema operativo en una lección (`video` con `windows`, `macos`, `linux`). |

## Aprobación

- [x] Revisado por Juan.
- [x] Revisado por Byron (cambios pedidos el 8-oct, aplicados en esta versión).
- [ ] Aprobado otra vez por la coordinación: la versión anterior duraba 255 min;
      esta dura 86.

Cambio del 15-oct (OnDemand sale del curso, 82 min):

- [x] Revisado por Juan.
- [ ] Revisado por Byron.
- [ ] Informado a la coordinación (la instalación en los clústeres ya está
      aprobada).

Cambio del 12-nov (sale la VPN, entra conda, 90 min):

- [ ] Revisado por Juan.
- [ ] Revisado por Byron.
