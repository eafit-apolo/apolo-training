---
id: m05/trabajos
titulo: Trabajos con Slurm
orden: 1
duracion: 13
video: m05-trabajos
practicas: [memoria]
quiz:
  # ─── Pregunta 1: qué significa PD y dónde se ve la razón ───────────────────

  - clave: m05-estado-pd
    enunciado: >-
      En `squeue`, tu trabajo aparece en estado `PD` y la última columna dice
      `(Priority)`. ¿Qué está pasando?

    opciones:
      # Correcta
      - texto: >-
          Está en espera: hay trabajos con más prioridad que van primero, y
          arranca solo cuando le llegue el turno.
        correcta: true

      # Incorrecta
      - texto: Está corriendo, pero con prioridad baja.

      # Incorrecta
      - texto: Falló, y Slurm lo va a reintentar más tarde.

      # Incorrecta
      - texto: Está detenido hasta que yo lo vuelva a enviar.

    explicacion: >-
      `PD` (_pending_) quiere decir que el trabajo espera en la cola; todavía no
      ha empezado a correr. La última columna de `squeue`, `NODELIST(REASON)`,
      dice por qué espera: `(Priority)` es que otros trabajos van primero y
      `(Resources)`, que no hay núcleos o memoria libres ahora. Las dos son
      normales: no hay que volver a enviarlo. Cuando arranca, pasa a `R`.

  # ─── Pregunta 2: por qué falló por memoria ─────────────────────────────────

  - clave: m05-sin-memoria
    enunciado: >-
      `sacct` dice que tu trabajo terminó en `OUT_OF_MEMORY`. ¿Qué haces?

    opciones:
      # Correcta
      - texto: Pido más memoria con `--mem` y lo envío de nuevo.
        correcta: true

      # Incorrecta
      - texto: Le pido más tiempo con `--time` y lo envío de nuevo.

      # Incorrecta
      - texto: Lo corro en el nodo de login, que tiene más memoria.

      # Incorrecta
      - texto: Lo envío otra vez igual; a la segunda suele pasar.

    explicacion: >-
      Slurm detuvo el trabajo porque usó más memoria de la que pidió con
      `--mem`, y va a pasar lo mismo cada vez que lo envíes igual: el tiempo no
      tiene que ver. Pide más con `--mem`, con un poco de margen. El nodo de
      login nunca es para cómputo: lo comparten todos los usuarios.
---

## Objetivos

Al terminar podrás:

- Escribir un script con directivas `#SBATCH` y enviarlo con `sbatch`.
- Elegir la partición de tu clúster.
- Seguir tus trabajos en la cola con `squeue`, entender su estado y su razón de
  espera, y cancelarlos con `scancel`.
- Revisar con `sacct` cómo terminó un trabajo y cuánta memoria usó.

## Resumen

En el nodo de login escribes tus archivos y envías trabajos; el cálculo corre
en un nodo de cómputo cuando Slurm le da turno a tu trabajo.

### 1. Un trabajo es un script

```bash
#!/bin/bash
#SBATCH --job-name=<nombre>
#SBATCH --partition=<partición>
#SBATCH --mem=1G
#SBATCH --time=00:10:00
#SBATCH --output=%x-%j.out

python3 <programa>.py
```

- Las líneas `#SBATCH` son las directivas: lo que le pides a Slurm. Van
  seguidas, justo después de `#!/bin/bash` y antes del primer comando; las que
  estén más abajo, Slurm no las lee.
- `--partition`: la partición donde va a correr (sección 2). Escríbela
  siempre.
- `--mem`: la memoria de todo el trabajo (`500M`, `1G`, `4G`). Si el programa
  usa más, Slurm lo detiene y el trabajo termina en `OUT_OF_MEMORY`.
- `--time`: el tiempo máximo, en `horas:minutos:segundos`. Al cumplirse, Slurm
  lo detiene (`TIMEOUT`).
- `--output`: el archivo donde queda lo que imprime el programa. `%x` es el
  nombre del trabajo y `%j`, su número (JobID).
- Debajo van los comandos, como si los escribieras en la terminal: cargar
  módulos (módulo 4) y correr tu programa.
- Pide siempre `--mem` y `--time` cercanos a lo que usas. Si omites `--mem`,
  la partición aparta una memoria por núcleo que puede ser mucho más de la que
  necesitas (tabla de abajo). Los núcleos se piden en el módulo 6.

### 2. Las particiones de tu clúster

Una partición es una cola con sus propias reglas (tiempo máximo, tipo de
nodos). Escríbela siempre en tu script, con `#SBATCH --partition=<partición>`,
aunque tu clúster tenga una por defecto: así no dependes de ella.

::: apolo2

| Partición  | Tiempo máximo | Memoria por núcleo sin `--mem` |
| ---------- | ------------- | ------------------------------ |
| `longjobs` | 14 días       | 1875 MB                        |
| `bigmem`   | 14 días       | 8000 MB                        |
| `accel`    | 14 días       | 1875 MB                        |
| `accel-2`  | 14 días       | 1875 MB                        |
| `learning` | 3 días        | 1900 MB                        |

En `sinfo`, el asterisco de `longjobs*` marca la partición por defecto: un
trabajo que no dice la partición cae ahí. Pon siempre `--time`: sin él, el
trabajo depende de la configuración de la partición.

:::

::: apolo3

| Partición  | Tiempo máximo | Memoria por núcleo sin `--mem` |
| ---------- | ------------- | ------------------------------ |
| `bigmem`   | 4 días        | 7500 MB                        |
| `longjobs` | 6 días        | 5700 MB                        |
| `accel`    | 3 días        | 4000 MB                        |

No hay partición por defecto: si tu script no dice la partición, `sbatch`
falla. Sin `--time`, el trabajo recibe 2 horas. En la VM de práctica, `sinfo`
te muestra `longjobs*` con asterisco; en Apolo III no hay ninguna marcada.

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

:::

En la VM de práctica ves las particiones de tu clúster, pero todas corren en la
misma máquina, con un máximo de 15 minutos por trabajo y dos trabajos tuyos a
la vez.

### 3. Enviar un trabajo

```bash
sbatch <script>.sh
```

```text
Submitted batch job 1234
```

Ese número es el JobID: con él sigues, cancelas y revisas el trabajo. La
partición y lo demás ya van en el script.

Para enviarlo una vez a otra partición sin editarlo, usa `-p`: manda sobre la
línea `#SBATCH --partition` del script.

```bash
sbatch -p <partición> <script>.sh
```

### 4. Seguirlo en la cola

```bash
squeue -u $USER
```

```text
JOBID PARTITION     NAME      USER ST   TIME  NODES NODELIST(REASON)
 1235    <part> <nombre> <usuario> PD   0:00      1 (Priority)
 1234    <part> <nombre> <usuario>  R   1:12      1 <nodo>
```

- `ST` es el estado: `PD`, en espera; `R`, en ejecución; `CG`, terminando.
  Cuando termina, sale de `squeue`. Justo después de enviarlo puede decir
  `(None)`: Slurm todavía no lo ha revisado.
- En un trabajo en espera, la última columna dice por qué: `(Priority)`, otros
  van primero; `(Resources)`, no hay núcleos o memoria libres ahora;
  `(QOSMaxJobsPerUserLimit)`, ya tienes corriendo todos los trabajos que se te
  permiten a la vez. Las tres son normales: el trabajo arranca solo cuando le
  toca.

### 5. Cancelarlo

```bash
scancel <JobID>
```

Funciona en espera o en ejecución, y solo con tus trabajos.

### 6. Ver cómo terminó

```bash
sacct -j <JobID>
sacct -j <JobID> -o JobID,JobName,State,Elapsed,ReqMem,MaxRSS
cat <nombre>-<JobID>.out
```

```text
JobID           JobName      State    Elapsed     ReqMem     MaxRSS
------------ ---------- ---------- ---------- ---------- ----------
1234           <nombre>  COMPLETED   00:00:21         1G
1234.batch        batch  COMPLETED   00:00:21                 3816K
1234.extern      extern  COMPLETED   00:00:21
```

- `State` dice cómo terminó: `COMPLETED` (bien), `FAILED` (el programa dio un
  error), `OUT_OF_MEMORY` (usó más memoria de la pedida), `TIMEOUT` (se le
  acabó el tiempo) o `CANCELLED` (lo cancelaste).
- `sacct` corta los textos de más de 10 letras con `+`: `OUT_OF_ME+` es
  `OUT_OF_MEMORY` y `CANCELLED+`, `CANCELLED by …`. Para ver la columna
  completa, ponle el ancho: `State%15`.
- Cada trabajo trae varias filas: la del trabajo y las de sus pasos (`.batch`
  es tu script). `MaxRSS`, la memoria máxima que usó, sale en la fila del paso.
  Es aproximada: Slurm la mide cada cierto tiempo, así que en un trabajo de
  pocos segundos, o en uno que detuvo por memoria, puede salir mucho más baja
  de lo real.
- Sin `-j`, `sacct` solo muestra los trabajos de hoy.

## Práctica

En la VM de práctica (`apolo-training.apolo.eafit.edu.co`), dentro de
`~/apolo-training`. Usa esta partición:

::: apolo2

`learning`, la misma de tu graduación en Apolo II.

:::

::: apolo3

`bigmem`, la misma de tu graduación en Apolo III.

:::

Primero, los estados de la cola:

1. Entra a la carpeta del curso:

   ```bash
   cd ~/apolo-training
   ```

2. Envía tres veces un trabajo que solo espera un minuto. `--wrap` envía un
   comando sin escribir un script; como no hay script, la partición y lo demás
   van en la línea de comandos. Con la flecha hacia arriba y Enter lo repites:

   ```bash
   sbatch -p <partición> -J espera --mem=100M -t 00:02:00 --wrap "sleep 60"
   ```

3. Mira la cola. Dos trabajos están en `R` y el tercero en `PD`, con la razón
   `(QOSMaxJobsPerUserLimit)`: en la VM cada usuario tiene dos trabajos a la
   vez.

   ```bash
   squeue -u $USER
   ```

4. Cancela el que está en espera y vuelve a mirar la cola:

   ```bash
   scancel <JobID>
   squeue -u $USER
   ```

Ahora, el laboratorio de memoria:

5. Abre `curso.sh` con `nano curso.sh` y cambia tres cosas:
   - La partición: `#SBATCH --partition=<partición>`, con la de arriba.
   - El nombre: `#SBATCH --job-name=curso-memoria`. Deja `--mem=1G`.
   - La última línea, para que el programa use unos 1,7 GB:
     `python3 pi.py simple 100000000`.

   La línea `module load` que descomentaste en el módulo 4 se queda como está.

6. Envíalo:

   ```bash
   sbatch curso.sh
   ```

7. Cuando salga de `squeue`, mira cómo terminó. Debe decir `OUT_OF_MEMORY`
   (o `OUT_OF_ME+`), y el archivo de salida, un mensaje con `oom_kill`:

   ```bash
   sacct -j <JobID> -o JobID,JobName,State%15,ReqMem
   cat curso-memoria-<JobID>.out
   ```

8. Cambia `--mem=1G` por `--mem=4G`, envíalo de nuevo y revisa con `sacct` que
   termine en `COMPLETED`.
9. Verifica:

   ```bash
   apolo-training verificar memoria
   ```

## Si algo falla

- **`invalid partition specified: <partición>`:** la partición no existe en tu
  clúster o la escribiste mal. Revisa los nombres con `sinfo`. Si dice
  `<particion-curso>`, falta cambiar la línea `#SBATCH --partition` de
  `curso.sh` (paso 5).
- **`No partition specified or system default partition`:** tu script no dice
  la partición, y en Apolo III es obligatoria. Agrega
  `#SBATCH --partition=<partición>`.
- **El trabajo se queda en `PD` mucho tiempo:** mira la razón en la última
  columna de `squeue`. `(Priority)` y `(Resources)` son normales: espera su
  turno.
- **`(PartitionTimeLimit)` en `squeue`:** pediste con `--time` más que el
  máximo de la partición y ese trabajo nunca va a arrancar. Cancélalo con
  `scancel` y envíalo con un `--time` menor.
- **`sacct` no muestra tu trabajo:** sin `-j <JobID>` solo muestra los de hoy.
  Revisa el número que te dio `sbatch`.
- **El trabajo terminó en `FAILED` y el `.out` dice
  `ModuleNotFoundError: No module named 'numpy'`:** falta la línea
  `module load` del módulo 4 en `curso.sh`. Descoméntala y envíalo de nuevo.
- **`Primero envía 'curso-memoria' con --mem=1G y deja que falle.`:** el
  verificador no encuentra un trabajo con ese nombre. Revisa la línea
  `#SBATCH --job-name=curso-memoria` de `curso.sh`.
- **`Ya lo viste fallar por memoria; ahora sube --mem y vuelve a enviarlo.`:**
  falta el paso 8.
- **`Tu trabajo terminó sin que Slurm lo detuviera…`:** lo enviaste con más de
  `1G` o sin cambiar la última línea a `100000000`. Ponlo como en el paso 5,
  envíalo, deja que falle y sigue con el paso 8.
- **`apolo-training: command not found`:** carga el verificador con
  `module load apolo-training` y vuelve a correr el comando.

¿Sigue sin funcionar? Escribe a `apolo@eafit.edu.co` con tu usuario, el JobID,
el comando que corriste y el mensaje de error.
