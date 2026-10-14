---
# Plantilla de lección (C-01). Cópiala a content/es/mNN/<slug>.md, cambia los
# datos y borra los comentarios. Los ejemplos son del módulo 5 y solo muestran
# el formato: el contenido real de cada módulo lo escribe su tarea C-xx.
# Reglas completas: content/README.md. Esquema: content/schema/leccion.schema.json.

# mNN/slug. Debe coincidir con la ruta del archivo: content/es/m05/trabajos.md.
id: m05/trabajos
titulo: Trabajos con Slurm
# Posición dentro del módulo, desde 1.
orden: 1
# Minutos de la lección completa: video, práctica y quiz.
duracion: 13

# Opcional. Clave del video: el nombre del archivo sin el idioma
# (m05-trabajos-es.mp4 → m05-trabajos). La plataforma lo muestra arriba.
# En la lección de VPN, uno por sistema operativo:
#   video:
#     windows: m01-vpn-windows
#     macos: m01-vpn-macos
#     linux: m01-vpn-linux
video: m05-trabajos

# Opcional. Prácticas de la VM, con el nombre del verificador: conexion,
# terminal, archivos, modulos, memoria, nucleos o paralelo.
practicas: [memoria]

# Opcional. 1 o 2 preguntas por lección (8 en el quiz final, con
# quiz_final: true). La plataforma muestra el quiz al final de la lección.
# - clave: mNN- y un nombre corto; no se cambia aunque cambie el texto.
# - opciones: de 2 a 5. Marca solo las correctas con correcta: true; si hay más
#   de una correcta, la pregunta es de selección múltiple.
# - explicacion: por qué es así. Se muestra al responder, sin decir cuál opción
#   era la correcta, para que reintentar sirva.
quiz:
  - clave: m05-estado-pd
    enunciado: En `squeue`, tu trabajo aparece en estado `PD`. ¿Qué significa?
    opciones:
      - texto: Que espera turno en la cola.
        correcta: true
      - texto: Que está corriendo en un nodo.
      - texto: Que terminó con un error.
    explicacion: >-
      `PD` es _pending_: el trabajo espera en la cola. La columna
      `NODELIST(REASON)` de `squeue` dice por qué espera.
  - clave: m05-sin-memoria
    enunciado: Tu trabajo terminó en `OUT_OF_MEMORY`. ¿Qué haces?
    opciones:
      - texto: Pedir más memoria con `--mem` y enviarlo de nuevo.
        correcta: true
      - texto: Revisar con `sacct` cuánta memoria usó de verdad.
        correcta: true
      - texto: Correrlo en el nodo de login, que tiene más memoria.
    explicacion: >-
      Slurm detuvo el trabajo porque usó más memoria de la que pidió. Con
      `sacct` ves cuánta usó y con `--mem` pides lo que necesita. El nodo de
      login nunca es para cómputo.
---

<!--
Secciones fijas, en este orden. Sin título con #: el título sale del front
matter. El video va arriba y el quiz al final; los pone la plataforma, no se
escriben aquí.

- Objetivos: siempre.
- Resumen: siempre. Los comandos del video, no una lectura larga.
- Práctica: solo si la lección tiene prácticas.
- Si algo falla: siempre que haya comandos.
-->

## Objetivos

Al terminar podrás:

- Enviar un trabajo a Slurm con `sbatch` y seguirlo con `squeue`.
- Leer los estados de la cola y la razón de espera.
- Revisar con `sacct` cómo terminó un trabajo.

## Resumen

<!--
Los comandos del video, en el mismo orden. Comandos en bloques bash sin el $;
lo que el usuario cambia, entre <ángulos>; las salidas, en bloques text.
En Slurm, siempre -p <partición>.
-->

Un trabajo es un script con directivas `#SBATCH` al inicio:

```bash
#!/bin/bash
#SBATCH --job-name=<nombre>
#SBATCH --partition=<partición>
#SBATCH --mem=1G
#SBATCH --time=00:10:00

python3 <programa>.py
```

Envíalo y síguelo:

```bash
sbatch <script>.sh
squeue -u $USER
sacct -j <JobID>
```

```text
JOBID  PARTITION  NAME      USER     ST  TIME  NODES  NODELIST(REASON)
1234   <part>     <nombre>  <user>   PD  0:00  1      (Priority)
```

<!--
Pestañas Apolo II / Apolo III: un bloque ::: apolo2 y otro ::: apolo3, seguidos.
La plataforma los muestra como pestañas y abre la del clúster del usuario.
Úsalas solo donde algo cambia entre los dos clústeres. Deja una línea en
blanco después de ::: apolo2 / ::: apolo3 y antes de cada :::.
-->

::: apolo2

La partición por defecto es `longjobs` (hasta 14 días). También están `bigmem`,
`accel`, `accel-2` y `learning`. Aun así, escribe siempre `-p <partición>`.

:::

::: apolo3

No hay partición por defecto: sin `-p <partición>`, `sbatch` falla. Las
particiones son `bigmem`, `longjobs` y `accel`.

:::

## Práctica

<!--
Pasos numerados, uno por acción, cada uno con un resultado que el usuario pueda
ver. El último paso siempre es apolo-training verificar <práctica>, con la
práctica del front matter. Cada comando se prueba en la VM antes de publicarlo.
-->

En la VM de práctica (`apolo-training.apolo.eafit.edu.co`):

1. Entra a la carpeta del curso y abre el script:

   ```bash
   cd ~/apolo-training
   nano curso.sh
   ```

2. Cambia el nombre del trabajo a `--job-name=curso-memoria`, deja
   `--mem=1G` y guarda.
3. Envía el trabajo:

   ```bash
   sbatch -p <partición> curso.sh
   ```

4. Cuando termine, mira cómo terminó. Debe decir `OUT_OF_MEMORY`:

   ```bash
   sacct -j <JobID> -o JobID,State,MaxRSS
   ```

5. Cambia `--mem=1G` por `--mem=4G` y envíalo de nuevo hasta que termine en
   `COMPLETED`.
6. Verifica:

   ```bash
   apolo-training verificar memoria
   ```

## Si algo falla

<!--
Los errores que de verdad aparecen, con el mensaje tal como sale y qué hacer.
Al final, siempre a quién escribir.
-->

- **`sbatch: error: invalid partition specified`:** la partición no existe en
  tu clúster. Revisa el nombre con `sinfo`.
- **El trabajo se queda en `PD` mucho tiempo:** mira la razón en la última
  columna de `squeue`. `(Priority)` o `(Resources)` es normal: espera su turno.
- **`apolo-training verificar memoria` dice que falta un trabajo:** revisa que
  el nombre del trabajo sea `curso-memoria`, el que trae `curso.sh`.

¿Sigue sin funcionar? Escribe a `apolo@eafit.edu.co` con tu usuario, el JobID,
el comando y el mensaje de error.
