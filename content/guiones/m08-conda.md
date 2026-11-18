# Guion: Ambientes de conda

| Dato              | Valor                                                               |
| ----------------- | ------------------------------------------------------------------- |
| Lección           | `m08/conda` (la escribe la C-14)                                    |
| Archivo del video | `m08-conda-es.mp4`                                                  |
| Graba             | Byron                                                               |
| Escena de OBS     | `Terminal`                                                          |
| Duración estimada | **4 min 15 s** (≈ 415 palabras a 130 por minuto + 60 s de comandos) |

Qué es conda y para qué sirve, crear un ambiente con conda-forge, activarlo,
instalar en él, usarlo dentro de un trabajo de Slurm y cuidar la cuota del
home. Responde lo que se pregunta en cada inducción: si tu software se instala
con conda, úsalo sin miedo. Los comandos y el orden deben coincidir con el
resumen de la C-14.

## Antes de grabar

- Se graba en un **clúster real** con una cuenta de demostración, porque la
  práctica de este módulo es en el clúster del usuario, no en la VM. Sin
  ambientes previos en esa cuenta.
- Por confirmar en Apolo II y en Apolo III con la C-14, antes de grabar:
  - Que `conda activate` funcione después de `module load miniconda3`, sin
    `conda init`. Si no funciona, el guion pasa a usar la línea `eval` también
    en la terminal.
  - Que la línea `eval "$(conda shell.bash hook)"` active el ambiente dentro
    del trabajo.
  - Dónde quedan los ambientes y el caché (se espera `~/.conda`) y cuánto pesa
    el ambiente de ejemplo, para decir la cifra real en «Cuidar la cuota».
  - La partición del trabajo de ejemplo en ese clúster.
- El script `conda.sh` ya escrito (ver «Dentro de un trabajo»).
- **En la edición:** cortar la espera mientras conda resuelve y descarga, y
  tapar nombres de nodos si salen en la salida del trabajo.

## Guion

### 0:00 · Entrada

| Qué se dice                                                                                                                | Qué se muestra                                |
| -------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| «Hola. En este video vas a crear un ambiente de conda, instalar en él tu propio software y usarlo en un trabajo de Slurm.» | La terminal en el login, con el prompt corto. |

### 0:10 · Qué es conda

| Qué se dice                                                                                                                                                                                                                                   | Qué se muestra     |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| «Los módulos traen el software que instaló el equipo de Apolo. Pero muchas veces necesitas un paquete que no está, o una versión distinta. Para eso está conda.»                                                                              | La terminal vacía. |
| «Conda instala software en tu carpeta personal, sin permisos de administrador. Y lo organiza en ambientes: cada ambiente es una caja aparte, con su propio Python y sus propios paquetes. Así un proyecto no le cambia las versiones a otro.» | La terminal vacía. |
| «Si tu software se puede instalar con conda, úsalo sin miedo.»                                                                                                                                                                                | La terminal vacía. |

### 0:50 · Cargar conda

| Qué se dice                                                     | Qué se muestra                                                 |
| --------------------------------------------------------------- | -------------------------------------------------------------- |
| «Conda viene en un módulo. Cárgalo con module load miniconda3.» | Se escribe `module load miniconda3` y luego `conda --version`. |

### 1:05 · Crear el ambiente

| Qué se dice                                                                                                                        | Qué se muestra                                                                                 |
| ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| «Para crear un ambiente: conda create, guion n y el nombre que quieras. Aquí, analisis.»                                           | Se escribe `conda create -n analisis` sin pulsar Enter.                                        |
| «Con guion c conda-forge, y override-channels, le dices que baje los paquetes solo de conda-forge, el canal libre y más completo.» | Se completa con `-c conda-forge --override-channels`.                                          |
| «Y al final, lo que quieres instalar. Aquí, Python tres punto doce y pandas.»                                                      | Se completa con `python=3.12 pandas` y Enter.                                                  |
| «Conda te muestra todo lo que va a instalar y pregunta si sigues. Escribe y.»                                                      | La lista de paquetes y `Proceed ([y]/n)?`; se escribe `y`. La descarga se corta en la edición. |

### 2:00 · Activarlo y usarlo

| Qué se dice                                                                                                                  | Qué se muestra                                                                      |
| ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| «Para usarlo, conda activate analisis. El prompt muestra el nombre del ambiente entre paréntesis.»                           | Se escribe `conda activate analisis`; se señala `(analisis)` en el prompt.          |
| «Ahora Python es el del ambiente, y pandas está ahí.»                                                                        | Se escribe `python -c "import pandas; print(pandas.__version__)"`; sale la versión. |
| «Si te falta otro paquete, lo agregas con conda install, con el ambiente activo. Para salir del ambiente, conda deactivate.» | Se escribe `conda deactivate`; desaparece `(analisis)` del prompt.                  |
| «Un consejo: no corras conda init. Cambia tu bashrc y activa conda en cada sesión, y eso choca con los módulos.»             | Texto sobre la terminal (Canva): «No corras `conda init`».                          |

### 2:45 · Dentro de un trabajo

| Qué se dice                                                                                                                                                                             | Qué se muestra                                                                                                                      |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| «Como con los módulos, el trabajo de Slurm corre en un nodo de cómputo y tiene que activar el ambiente por su cuenta.»                                                                  | Se escribe `cat conda.sh`.                                                                                                          |
| «En el script, después de las directivas, cargas miniconda3, preparas conda con esta línea eval, activas el ambiente y corres tu programa. La línea eval cópiala tal cual del resumen.» | Se señalan en orden: `module load miniconda3`, `eval "$(conda shell.bash hook)"`, `conda activate analisis` y la línea de `python`. |
| «Lo envías con sbatch y, como siempre, con guion p y la partición de tu clúster.»                                                                                                       | Se escribe `sbatch -p <partición> conda.sh` y luego `squeue --me`.                                                                  |
| «Cuando termina, en la salida está la versión de pandas: el trabajo usó tu ambiente.»                                                                                                   | Se escribe `cat slurm-<JobID>.out`; sale la versión.                                                                                |

### 3:35 · Cuidar la cuota

| Qué se dice                                                                                                                                                | Qué se muestra                                                                   |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| «Un cuidado: los ambientes viven en tu home, y pesan. Este, con solo pandas, ya ocupa cientos de megas, y conda guarda una copia de todo lo que descarga.» | Se escribe `du -sh ~/.conda`; se señala el tamaño (decir la cifra real).         |
| «Con conda clean guion guion all borras esas copias. Y si ya no usas un ambiente, bórralo con conda env remove, guion n y el nombre.»                      | Se escribe `conda clean --all`, se acepta con `y` y se repite `du -sh ~/.conda`. |

### 4:05 · Salida

| Qué se dice                                                                                                                                                                                   | Qué se muestra                                        |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| «Ahora hazlo en tu clúster: crea tu ambiente, instala un paquete y úsalo en un trabajo corto, con guion p. Esta práctica no la revisa el verificador. Luego responde las preguntas de abajo.» | La sección «Práctica» de la lección en la plataforma. |

## El script de ejemplo

```bash
#!/bin/bash
#SBATCH --job-name=conda-prueba
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00

module load miniconda3
eval "$(conda shell.bash hook)"
conda activate analisis

python -c "import pandas; print(pandas.__version__)"
```

## Revisión

- [ ] Comandos probados en Apolo II y en Apolo III (C-14).
- [ ] Revisado por Juan antes de grabar.
- [ ] Dura 5 minutos o menos ya editado.
