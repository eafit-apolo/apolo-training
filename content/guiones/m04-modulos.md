# Guion: Módulos

| Dato              | Valor                                                          |
| ----------------- | -------------------------------------------------------------- |
| Lección           | `m04/modulos` (la escribe la C-06)                             |
| Archivo del video | `m04-modulos-es.mp4`                                           |
| Graba             | Byron                                                          |
| Escena de OBS     | `Terminal`                                                     |
| Duración estimada | **3 min** (≈ 280 palabras a 130 por minuto + 50 s de comandos) |

Qué es un módulo y por qué no se instala nada; `module avail`, `module spider`,
`module load`, `module list` y `module purge`; el paso extra de Apolo III; y
dónde va el `module load` para que funcione en un trabajo. Los comandos y el
orden deben coincidir con el resumen de la C-06.

## Antes de grabar

- Sesión en la VM de práctica con una cuenta de demostración, perfil
  `apolo3`, para que el mensaje de bienvenida muestre el `module use`.
- El ejemplo es **`py3-scipy`**, no el módulo de numpy del laboratorio, para no
  darle la respuesta al usuario. Por confirmar en la VM antes de grabar:
  - Que `module spider scipy` lo encuentre y que
    `module spider py3-scipy/<versión>` diga qué cargar antes.
  - Que, con el módulo cargado, `python3 -c "import scipy"` funcione.
  - Si no está en la VM, cambiarlo por otro módulo que sí esté y no sea el del
    laboratorio, y ajustar el guion.
- Un script corto de ejemplo, `ejemplo.sh`, con un `module load` antes del
  programa (ver «Dentro de un trabajo»).
- **En la edición:** cortar la espera de `module avail` si tarda, y tapar
  nombres internos si alguno aparece en las rutas.

## Guion

### 0:00 · Entrada

| Qué se dice                                                                                          | Qué se muestra                             |
| ---------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| «Hola. En este video vas a buscar y cargar el software que necesitas con module, sin instalar nada.» | La terminal en la VM, con el prompt corto. |

### 0:10 · Qué es un módulo

| Qué se dice                                                                                                                                                                 | Qué se muestra     |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| «En Apolo no instalas programas con dnf ni con apt: no tienes permisos de administrador, y no hace falta. El software ya está instalado, muchas veces en varias versiones.» | La terminal vacía. |
| «Para usarlo, cargas un módulo. Un módulo prepara tu sesión para un programa: lo cargas cuando lo necesitas y lo quitas cuando terminas.»                                   | La terminal vacía. |

### 0:35 · Ver lo que hay: module avail

| Qué se dice                                                                                                      | Qué se muestra                                                                   |
| ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| «module avail lista lo que puedes cargar ahora mismo. Los que tienen una L ya están cargados: vienen al entrar.» | Se escribe `module avail`; se sube despacio por la salida y se señala una `(L)`. |

### 1:00 · Buscar en todo el árbol: module spider

| Qué se dice                                                                                                                                                                                    | Qué se muestra                                                                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| «Pero avail no lo muestra todo: hay programas que solo aparecen después de cargar otros. Para buscar en todo el árbol, usa module spider. Por ejemplo, scipy.»                                 | Se escribe `module spider scipy`; sale el nombre `py3-scipy` y su versión.                                                              |
| «Si le das el nombre con la versión, spider te dice qué tienes que cargar antes.»                                                                                                              | Se escribe `module spider py3-scipy/<versión>`; se señala el bloque `You will need to load all module(s)…`.                             |
| «En Apolo III hay un paso más. Algunos programas solo aparecen después de un module use con la ruta que te indica el mensaje de bienvenida. Lo tienes en la pestaña de Apolo III del resumen.» | Se señala la línea de `module use /opt/ohpc/pub/moduledeps/…` en el mensaje de bienvenida (subir en la terminal o mostrarla con Canva). |

### 1:50 · Cargar, ver y quitar

| Qué se dice                                                                  | Qué se muestra                                                                     |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| «Para cargarlo, module load y el nombre.»                                    | Se escribe `module load py3-scipy`.                                                |
| «module list muestra lo que tienes cargado. Ahí está.»                       | Se escribe `module list`; se señala `py3-scipy`.                                   |
| «Y ahora Python encuentra scipy.»                                            | Se escribe `python3 -c "import scipy; print(scipy.__version__)"`; sale la versión. |
| «Si quieres empezar de cero, module purge quita todos los módulos cargados.» | Se escribe `module purge` y luego `module list`, que ya no muestra nada.           |

### 2:30 · Dentro de un trabajo

| Qué se dice                                                                                                                                                        | Qué se muestra                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| «Lo más importante: tu trabajo de Slurm no corre en esta terminal, sino en un nodo de cómputo. Por eso el module load va dentro del script, antes de tu programa.» | Se escribe `cat ejemplo.sh`; se señala la línea `module load py3-scipy` encima de la línea de `python3`. |
| «Así el trabajo carga lo mismo cada vez, sin depender de lo que tengas cargado en la terminal cuando lo envías.»                                                   | El mismo script, quieto.                                                                                 |

### 2:45 · Salida

| Qué se dice                                                                                                                                                                    | Qué se muestra                                        |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| «En el laboratorio de abajo hay un trabajo que falla porque le falta un módulo. Encuéntralo con module spider, cárgalo en el script y corre apolo-training verificar modulos.» | La sección «Práctica» de la lección en la plataforma. |

## Revisión

- [ ] Ejemplo de `py3-scipy` probado en la VM.
- [ ] Revisado por Juan antes de grabar.
- [ ] Dura 5 minutos o menos ya editado.
