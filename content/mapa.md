# Mapa de contenidos del curso (A-12)

Alcance exacto del curso de inducción: qué enseña cada módulo, qué video lo
explica, qué práctica hace el usuario y qué preguntas responde. Las tareas de
contenido (C-xx), videos (M-xx) y el importador (B-04) parten de aquí. Si algo
cambia, se cambia primero en este archivo.

## Cómo es el curso

- **Dura entre 60 y 90 minutos en total**, contando videos, quices y práctica.
  Es lo que toma hoy una inducción presencial; más largo, la gente no lo
  termina.
- **Cada módulo es: video corto + quiz de 1 o 2 preguntas + práctica en la VM.**
  El video explica; debajo va un resumen con los comandos para copiarlos y
  consultarlos después, no una lectura larga.
- **Toda la práctica es real, en la VM de práctica**
  (`apolo-training.apolo.eafit.edu.co`). El usuario escribe los comandos de
  verdad, desde la terminal de la plataforma o con su propio cliente SSH. No hay
  terminales simuladas: la VM es un entorno seguro, donde un error solo afecta
  al propio usuario.
- **La graduación es en su clúster real** (Apolo II o Apolo III), con OnDemand.

## Resumen

| Módulo                       | Videos                                                    | Práctica en la VM                                       | Preguntas |    Min | Quién |
| ---------------------------- | --------------------------------------------------------- | ------------------------------------------------------- | --------: | -----: | ----- |
| 0 · Bienvenida               | Bienvenida (2 min)                                        | —                                                       |         2 |      3 | Byron |
| 1 · Conexión                 | VPN de su sistema operativo (3 min) y SSH (2 min)         | Conectarse con su cliente SSH y cambiar la contraseña ✔ |         2 |     11 | Byron |
| 2 · Terminal y Linux         | Terminal y Linux (4 min)                                  | Carpeta del curso, copiar el laboratorio y nano ✔       |         2 |     10 | Juan  |
| 3 · Archivos y transferencia | Archivos (3 min)                                          | Subir un archivo con `scp` y ver cuánto ocupa ✔         |         2 |      8 | Juan  |
| 4 · Software con módulos     | Módulos (3 min)                                           | Laboratorio de módulos ✔                                |         2 |      9 | Byron |
| 5 · Trabajos con Slurm       | Trabajos (5 min)                                          | Laboratorio de memoria ✔ y estados de la cola           |         2 |     13 | Juan  |
| 6 · Núcleos y paralelismo    | Paralelismo (4 min)                                       | Laboratorios de núcleos y paralelo ✔                    |         2 |     14 | Juan  |
| 7 · OnDemand y VS Code       | OnDemand (video de Sofía, ya existe) y VS Code (2 min)    | Graduación en su clúster real ✔ (VS Code opcional)      |         2 |     13 | Juan  |
| 8 · Cierre                   | —                                                         | —                                                       | 8 (final) |      5 | Juan  |
| **Total**                    | **11 por grabar + 1 existente; cada usuario ve ≈ 33 min** | **7 prácticas verificadas + graduación**                |    **24** | **86** |       |

✔ = lo revisa el verificador `apolo-training` y aparece en Mi progreso.

- **Videos por grabar (11):** bienvenida, VPN en Windows, VPN en macOS, VPN en
  Linux, SSH, terminal y Linux, archivos, módulos, trabajos, paralelismo y VS
  Code. Cada usuario ve solo el de VPN de su sistema operativo. Todos de 5
  minutos o menos, en español con subtítulos en español e inglés.
- **Video existente:** el de OnDemand que hizo Sofía (se publica en la sección
  _Tutorials_ de apolo-docs). No se graba de nuevo; se enlaza o se incrusta.
- **Todas las prácticas se verifican igual:** cada una termina con
  `apolo-training verificar <práctica>` en la VM y su resultado llega a Mi
  progreso. Son siete: `conexion`, `terminal`, `archivos`, `modulos`,
  `memoria`, `nucleos` y `paralelo`. La graduación se verifica en el clúster
  real.
- **Quién:** responde por el video, el resumen y el quiz del módulo. Los videos
  quedan parejos: Byron graba 6 (unos 16 min) y Juan 5 (unos 18 min); ver
  «Reparto de videos».
- **Minutos por módulo:** video + práctica + quiz (unos 30 segundos por
  pregunta). La práctica opcional de VS Code no cuenta.

## Reglas para el contenido

- **Video primero.** Lo que haga falta explicar va en el video. Debajo, un
  resumen corto con los comandos del video, en bloques `bash` sin el `$` y con
  los valores para reemplazar entre `<ángulos>`.
- **Pestañas Apolo II / Apolo III** en el resumen donde algo cambia. La
  plataforma abre la del clúster del usuario.
- **Siempre `-p <partición>` en los comandos de Slurm:** Apolo III no tiene
  partición por defecto y `sbatch` sin `-p` falla (A-03).
- **Quiz corto:** 1 o 2 preguntas por módulo, que se respondan en menos de 30
  segundos cada una, con la explicación de la respuesta.
- **Práctica con instrucciones numeradas** y un resultado que el usuario pueda
  comprobar. Cada comando se prueba en la VM y en el clúster real que
  corresponda.
- Sin datos de usuarios reales, IPs ni nombres internos: el repo será público.

## Módulos

Cada lección se identifica como `mNN/slug`, que es también su ruta en la
plataforma.

### 0 · Bienvenida · 3 min

| Lección          | Trae                             |
| ---------------- | -------------------------------- |
| `m00/bienvenida` | video (2 min), resumen, quiz (2) |

- **Video:** qué es Apolo, Apolo II frente a Apolo III y cuál es el suyo, que el
  login no es para cómputo (los trabajos van por Slurm a nodos compartidos) y
  cómo funciona el curso: VM de práctica, laboratorios y graduación.
- **Quiz (2):** qué se hace y qué no en el login; qué hace falta para aprobar.

### 1 · Conexión · 11 min

| Lección   | Trae                                                          |
| --------- | ------------------------------------------------------------- |
| `m01/vpn` | video de VPN de su sistema operativo (Windows, macOS o Linux) |
| `m01/ssh` | video SSH (2 min), práctica en la VM, quiz (2)                |

- **Videos de VPN:** uno por sistema operativo, de 3 minutos o menos, con
  GlobalProtect. El usuario elige el suyo y no tiene que ver los otros. Se
  enlaza la guía vigente de apolo-docs (_Configure the VPN_). Hoy no hay doble
  factor (A-08).
- **Video SSH:** conectarse al login (`apolo.eafit.edu.co` o
  `apolo-3.eafit.edu.co`), la huella del servidor y el cambio de contraseña en
  el primer ingreso.
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
  `cp -r`, `mv`, `rm` (no hay papelera), `cat` y `nano` (guardar y salir). Los
  permisos solo se leen con `ls -l`; no se enseña `chmod`: los scripts de Slurm
  no lo necesitan y mal usado deja los archivos expuestos a otros usuarios.
- **Práctica:**
  1. Crear `~/curso` y entrar.
  2. Copiar el laboratorio desde la carpeta compartida del curso (ruta de la
     P-04).
  3. Abrir `LEEME.txt` con nano, escribir su nombre y guardar.
  4. Comprobar con `ls -l` y `cat`.
  5. `apolo-training verificar terminal`.
- **Quiz (2):** qué hace `rm` (no hay papelera); cómo salir de nano guardando.

### 3 · Archivos y transferencia · 8 min

| Lección        | Trae                                                             |
| -------------- | ---------------------------------------------------------------- |
| `m03/archivos` | video (3 min), resumen con pestañas, práctica en la VM, quiz (2) |

- **Video:** dónde está el home en cada clúster y cuánto cabe, `du -sh`,
  `quota -s`, `scp` para archivos sueltos y `rsync -av` para carpetas grandes
  (no se enseña `--delete`).
- **Pestañas del resumen:** Apolo II, home por NFS (cuota por confirmar, A-04);
  Apolo III, home en el nodo maestro con aviso a los 150 GB y límite en 200 GB.
- **Práctica:**
  1. Desde su computador,
     `scp <archivo> <usuario>@apolo-training.apolo.eafit.edu.co:~/curso/`.
  2. En la VM, `ls ~/curso` y `du -sh ~/curso`.
  3. `apolo-training verificar archivos`.
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
  gcc 14.2 en Apolo III (A-04).
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

### 7 · OnDemand y VS Code · 13 min

| Lección        | Trae                                                                |
| -------------- | ------------------------------------------------------------------- |
| `m07/ondemand` | video de OnDemand (Sofía, ya existe), graduación en el clúster real |
| `m07/vscode`   | video (2 min), práctica opcional, quiz (2)                          |

- **Video de OnDemand:** el de Sofía, enlazado desde apolo-docs o incrustado.
  Cubre archivos, aplicaciones interactivas y que cerrar la pestaña no libera
  los recursos.
- **Graduación (V-07):**
  1. Con la VPN, abrir una sesión interactiva de OnDemand en su clúster.
  2. Cerrarla desde _My Interactive Sessions_.
  3. Por SSH al login: `module load apolo-training` y
     `apolo-training verificar ondemand JOBID`.
  4. Pegar el JobID y la salida en Mi progreso.
- **Video de VS Code:** Remote-SSH para editar; el cómputo va por Slurm, nunca
  en el login; cerrar la conexión al terminar.
- **Práctica opcional:** Remote-SSH a `apolo-training.apolo.eafit.edu.co`.
- **Quiz (2):** qué pasa al cerrar la pestaña de OnDemand; para qué sí y para
  qué no sirve VS Code en el login.

### 8 · Cierre · 5 min

| Lección      | Trae                                        |
| ------------ | ------------------------------------------- |
| `m08/cierre` | resumen de cómo pedir ayuda, quiz final (8) |

- **Pedir ayuda:** correo `apolo@eafit.edu.co` con clúster, usuario, JobID,
  comando, salida del error y qué se esperaba. Documentación en
  <https://apolo-docs.readthedocs.io>.
- **Qué sigue:** con todo aprobado, el equipo aplica la QOS normal en su clúster
  real.
- **Quiz final (8):** una pregunta de cada módulo del 1 al 7, más una de
  integración; se aprueba con 80 % (7 de 8).

## Reparto de videos

| Quién | Videos                                                                                       | Cantidad | Minutos |
| ----- | -------------------------------------------------------------------------------------------- | -------: | ------: |
| Byron | Bienvenida (2), VPN en Windows (3), VPN en macOS (3), VPN en Linux (3), SSH (2), módulos (3) |        6 |    ≈ 16 |
| Juan  | Terminal y Linux (4), archivos (3), trabajos (5), paralelismo (4), VS Code (2)               |        5 |    ≈ 18 |

Los tres de VPN siguen el mismo guion con distinto sistema operativo, por eso
Byron lleva uno más pero con menos minutos. El de OnDemand es el de Sofía y no
se graba.

## Pendientes que afectan este mapa

| Pendiente                                                        | Afecta        | Lo resuelve |
| ---------------------------------------------------------------- | ------------- | ----------- |
| Ruta de la carpeta compartida del laboratorio                    | módulo 2      | P-04, V-04  |
| Cuota del home de Apolo II, scratch y áreas compartidas          | módulo 3      | A-04        |
| Toolchain por defecto confirmado                                 | módulo 4      | A-04, I-06  |
| Nombre del módulo de Python con numpy                            | módulos 4 a 6 | I-07        |
| Qué OnDemand atiende a cada clúster y enlace del video de Sofía  | módulo 7      | A-04, Sofía |
| Qué revisa el verificador en `conexion`, `terminal` y `archivos` | módulos 1 a 3 | V-01, V-03  |
| Las 10 preguntas más repetidas en soporte                        | quices        | A-10        |

## Cambios que este mapa pide al plan

Se aplican a las tarjetas cuando se apruebe este PR.

| Tareas                 | Cambio                                                                                                                                                                                       |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-01, T-02, T-03, T-04 | Se eliminan: no hay terminales quemadas (libera unas 42 h: 30 de Juan y 12 de Byron).                                                                                                        |
| H-04 (go/no-go)        | «Terminal quemada» pasa a «práctica en la VM». La terminal real de la plataforma (T-06) cae después del 19-nov, así que el criterio se cumple con el cliente SSH del usuario.                |
| M-xx                   | De 5 videos a 11 por grabar, más el de Sofía; reparto parejo: Byron 6 (≈ 16 min) y Juan 5 (≈ 18 min). Hay que recalcular horas.                                                              |
| C-02 a C-11            | El texto se reduce a resúmenes bajo cada video. Responsables: Byron los módulos 0, 1 y 4; Juan los módulos 2, 3, 5, 6, 7 y 8. C-09 y C-10 se unen (módulo 7); C-11 pasa al módulo 8.         |
| V-01, V-03             | El verificador suma tres prácticas: `conexion`, `terminal` y `archivos` (siete en total).                                                                                                    |
| A-11 (diseño)          | Quitar la terminal quemada (`escenario`, `POST /api/progreso/terminal`), sumar `conexion`, `terminal` y `archivos` a `LabId` y permitir un video por sistema operativo en la lección de VPN. |

## Aprobación

- [x] Revisado por Juan.
- [ ] Revisado por Byron (cambios pedidos el 8-oct, aplicados en esta versión).
- [ ] Aprobado otra vez por la coordinación: la versión anterior duraba 255 min;
      esta dura 86.
