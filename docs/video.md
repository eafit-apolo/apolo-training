# Guía de grabación de videos (M-01)

Cómo se graban y editan los videos del curso para que todos salgan con
la misma calidad y el mismo estilo, los grabe quien los grabe. Los videos que
hay que hacer, su duración y quién graba cada uno están en
[`content/mapa.md`](../content/mapa.md).

Se graba con OBS Studio, que cada uno configura en su propio computador con
el tutorial de abajo, y se edita en Canva con la plantilla del curso, que ya
trae la intro y el cierre. Los videos nunca entran al repo: `.gitignore` ya
excluye `*.mp4`, `*.mkv`, `*.mov` y `*.webm`.

## Resumen

| Qué            | Valor                                                                   |
| -------------- | ----------------------------------------------------------------------- |
| Grabación      | OBS Studio, 1920×1080 a 30 fps, MP4 fragmentado                         |
| Escenas        | `Pantalla completa` y `Terminal`                                        |
| Terminal       | Fuente monoespaciada de 18 pt o más, tema de alto contraste             |
| Audio          | El mismo micrófono para todos, sala sin eco                             |
| Edición        | Canva, con la [plantilla del curso](https://canva.link/ensf5pnoj7t3sv9) |
| Intro y cierre | Los de la plantilla, iguales en todos los videos                        |
| Archivo final  | MP4 de 1080p descargado de Canva, 5 minutos o menos                     |
| Nombre         | `mNN-<lección>-es.mp4`, por ejemplo `m01-ssh-es.mp4`                    |
| Subtítulos     | `mNN-<lección>-es.vtt` y `mNN-<lección>-en.vtt`                         |

## Nombres de los archivos

`mNN-<lección>-<idioma>.<ext>`, en minúsculas, sin tildes ni espacios. `mNN` y
`<lección>` son los de la lección en el mapa (`m01/ssh` → `m01-ssh`). El idioma
es el del audio; todos los videos se graban en español y llevan subtítulos en
los dos idiomas.

| Video            | Archivo                  | Quién |
| ---------------- | ------------------------ | ----- |
| Bienvenida       | `m00-bienvenida-es.mp4`  | Byron |
| VPN en Windows   | `m01-vpn-windows-es.mp4` | Byron |
| VPN en macOS     | `m01-vpn-macos-es.mp4`   | Byron |
| VPN en Linux     | `m01-vpn-linux-es.mp4`   | Byron |
| SSH              | `m01-ssh-es.mp4`         | Byron |
| Terminal y Linux | `m02-terminal-es.mp4`    | Juan  |
| Archivos         | `m03-archivos-es.mp4`    | Juan  |
| Módulos          | `m04-modulos-es.mp4`     | Byron |
| Trabajos         | `m05-trabajos-es.mp4`    | Juan  |
| Paralelismo      | `m06-paralelismo-es.mp4` | Juan  |
| VS Code          | `m07-vscode-es.mp4`      | Juan  |

Los subtítulos llevan el mismo nombre con el idioma del texto:
`m01-ssh-es.vtt` y `m01-ssh-en.vtt`.

## Estilo

- **Intro y cierre iguales en todos los videos:** son los de la plantilla de
  Canva y no se editan. No mencionan el módulo ni el tema.
- **El tema del video lo dice la voz**, en la primera frase después de la
  intro, y la última frase antes del cierre dice qué hacer después. Ver
  [Frases de entrada y de salida](#frases-de-entrada-y-de-salida).
- **Se habla de tú**, en frases cortas, a unas 130 palabras por minuto. Un video
  de 5 minutos son unas 650 palabras de guion.
- **Los comandos se escriben en vivo**, despacio, y después de cada uno se deja
  1 o 2 segundos para leer la salida antes de hablar de ella.
- **Lo que se dice coincide con el resumen** de la lección: los mismos comandos
  y en el mismo orden.

### Frases de entrada y de salida

**Entrada:** justo después de la intro. Dice qué va a saber hacer la persona al
terminar el video, con los nombres reales de lo que se enseña, no solo el tema.
Fórmula: «Hola. En este video vas a <lo que va a poder hacer>».

- Bien: «En este video vas a conectarte por SSH al login de tu clúster y a
  cambiar la contraseña temporal».
- Mal: «En este video vas a aprender sobre SSH».

**Salida:** justo antes del cierre. Dice qué hacer ahora, según lo que siga en
la lección:

- **Si sigue una práctica:** qué se hace en la VM y con qué comando se
  comprueba.
- **Si sigue otro video:** cuál es y qué hay que dejar listo antes.
- **Si solo sigue el quiz:** que lo responda y a qué módulo pasa.

Las frases de cada video, a partir de [`content/mapa.md`](../content/mapa.md).
Se pueden decir con otras palabras, pero sin perder lo concreto. Si el mapa
cambia, se cambian aquí también.

| Video            | Entrada: «Hola. En este video vas a…»                                                                                                   | Salida                                                                                                                                                                             |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bienvenida       | …conocer Apolo, saber si vas a trabajar en Apolo II o en Apolo III y ver cómo funciona este curso.                                      | «Responde las dos preguntas de abajo y sigue con el módulo 1, donde te vas a conectar a Apolo por primera vez».                                                                    |
| VPN en Windows   | …instalar GlobalProtect en Windows y conectarte a la VPN de EAFIT, que necesitas para entrar a Apolo.                                   | «Ya tienes la VPN. Déjala encendida y sigue con el video de SSH».                                                                                                                  |
| VPN en macOS     | …instalar GlobalProtect en macOS y conectarte a la VPN de EAFIT, que necesitas para entrar a Apolo.                                     | «Ya tienes la VPN. Déjala encendida y sigue con el video de SSH».                                                                                                                  |
| VPN en Linux     | …instalar GlobalProtect en Linux y conectarte a la VPN de EAFIT, que necesitas para entrar a Apolo.                                     | «Ya tienes la VPN. Déjala encendida y sigue con el video de SSH».                                                                                                                  |
| SSH              | …conectarte por SSH al login de tu clúster, aceptar la huella del servidor y cambiar la contraseña temporal.                            | «Ahora es tu turno: conéctate a la VM de práctica, cambia tu contraseña y, al terminar, corre `apolo-training verificar conexion`».                                                |
| Terminal y Linux | …moverte entre carpetas, crear, copiar, mover y borrar archivos, y editar un archivo con nano.                                          | «Ahora practica en la VM: crea la carpeta del curso, copia el laboratorio, escribe tu nombre en `LEEME.txt` con nano y corre `apolo-training verificar terminal`».                 |
| Archivos         | …ver dónde quedan tus archivos en Apolo, cuánto espacio te queda y cómo subir archivos desde tu computador con scp y rsync.             | «Ahora sube un archivo de tu computador a la VM con scp, mira cuánto ocupa con `du -sh` y corre `apolo-training verificar archivos`».                                              |
| Módulos          | …buscar y cargar el software que necesitas con `module`, sin instalar nada.                                                             | «En el laboratorio de abajo hay un trabajo que falla porque le falta un módulo. Encuéntralo con `module spider`, cárgalo en el script y corre `apolo-training verificar modulos`». |
| Trabajos         | …escribir un script de Slurm, enviarlo con sbatch, seguirlo en la cola y ver cómo terminó.                                              | «En el laboratorio de memoria vas a ver un trabajo que se queda sin memoria y a corregirlo. Al final, corre `apolo-training verificar memoria`».                                   |
| Paralelismo      | …ver la diferencia entre los núcleos que reservas y los que tu programa usa de verdad, y por qué reservar de más perjudica a los demás. | «Ahora haz los dos laboratorios, núcleos y paralelo. Cada uno termina con `apolo-training verificar` y el nombre del laboratorio».                                                 |
| VS Code          | …conectar VS Code a Apolo con Remote-SSH para editar tus archivos, y ver para qué no debes usarlo.                                      | «Si quieres, pruébalo con la VM de práctica; es opcional. Luego responde las preguntas de abajo».                                                                                  |

## Antes de grabar

### Sala y micrófono

- **Un solo micrófono para todos.** El centro no tiene uno, así que hay que
  conseguir uno antes de grabar: un micrófono externo (USB o de solapa) o unos
  audífonos con micrófono. Todos los videos se graban con ese mismo, para que
  el audio suene igual en todo el curso. No se usa el micrófono del portátil.
- Micrófono de mesa o de solapa a 10 o 20 cm de la boca; con audífonos, la
  varilla del micrófono a un lado de la boca, no enfrente. Así no le pegan las
  «p» y las «b».
- Sala pequeña, con puerta y ventanas cerradas. El aire acondicionado no se
  puede apagar, pero no hace ruido; si se oye en la prueba de audio, el filtro
  de supresión de ruido lo quita. Si hay eco, sirven cortinas, un sofá o
  cualquier superficie blanda cerca.
- Celular en silencio y lejos del micrófono.

### Pantalla

- **Resolución del monitor en 1920×1080.** Si el monitor es más grande (1440p o
  4K), bajarlo a 1080p mientras se graba; si no, OBS reduce la imagen y la
  letra de 18 pt se ve a la mitad.
- Escala del sistema al 100 %, sin ampliación.
- Activar «No molestar» para que no salgan notificaciones.
- Fondo de escritorio liso, sin íconos.
- En el navegador: perfil limpio, sin barra de marcadores ni otras pestañas,
  zoom entre 125 y 150 %.

### Terminal

- Fuente monoespaciada de **18 pt o más** (recomendada: 20 pt en DejaVu Sans
  Mono, JetBrains Mono o la que traiga el sistema).
- Tema de **alto contraste**: texto claro sobre fondo negro o casi negro, sin
  transparencia ni imagen de fondo.
- Ventana a pantalla completa (F11). A 20 pt caben unas 100 columnas.
- Prompt corto, que no ocupe media línea:

  ```bash
  export PS1='\u@\h:\W\$ '
  ```

- `clear` antes de cada toma.

### Nada sensible en pantalla

- Usar una cuenta de demostración, nunca la personal. Las contraseñas se
  escriben con la grabación en pausa o se cortan en la edición.
- Sin correos, nombres de otras personas ni sesiones ajenas: en el clúster,
  `squeue --me` en vez de `squeue`.
- Sin IPs ni nombres internos de nodos o servidores. Si un comando los muestra,
  se corta o se tapa en la edición.
- No mostrar `history`, el portapapeles ni el gestor de contraseñas.

## Tutorial de OBS Studio

Escrito para OBS 32 en español. En Windows y macOS los menús son los mismos;
solo cambian los nombres de las fuentes de captura.

### 1. Perfil y colección de escenas

Para no mezclar esta configuración con la que ya se tenga en OBS:

1. **Perfil → Nuevo**, con el nombre `Apolo training`. OBS cambia a ese perfil.
2. **Colección de escenas → Nueva**, con el mismo nombre.

Si el asistente de configuración automática aparece, cerrarlo: los valores se
ponen a mano en el paso 2. Los pasos 2 a 5 se hacen una sola vez; después
basta con elegir el perfil y la colección antes de grabar.

### 2. Video y salida

En **Archivo → Configuración**:

1. **Video:** resolución base (lienzo) y de salida (escalada) en `1920x1080`,
   FPS comunes en `30`.
2. **Salida**, modo de salida **Simple**, sección Grabación:
   - Ruta de grabación: una carpeta fuera del repo, por ejemplo
     `~/Videos/apolo-training/crudos/`.
   - Calidad: **Alta calidad, tamaño de archivo medio**. Con calidad más alta
     los archivos pesan demasiado para subirlos a Canva.
   - Formato: **MP4 fragmentado**, que Canva abre directamente.
   - Codificador: **Software (x264)**, o el de hardware si el equipo se queda
     corto (NVENC o VAAPI).
3. **Audio:** frecuencia de muestreo `48 kHz`, canales `Estéreo`. Audio del
   escritorio **desactivado** (así no se cuelan notificaciones). Micrófono: el
   micrófono externo del equipo.

### 3. Escenas

En el panel **Escenas**, con el botón **+**:

- **`Pantalla completa`**: fuente **Captura de pantalla** (en Linux,
  _Captura de pantalla (PipeWire)_ en Wayland o _(XSHM)_ en X11). Para
  navegador, OnDemand, la VPN y VS Code.
- **`Terminal`**: fuente **Captura de ventana** (_PipeWire_ o _Xcomposite_)
  con la ventana de la terminal. Clic derecho sobre la fuente → **Transformar →
  Ajustar a la pantalla** (Ctrl+F). Para todo lo que pase en la terminal.

Las dos escenas comparten la fuente del micrófono; no hace falta añadirla a cada
una.

### 4. Filtros del micrófono

En el **Mezclador de audio**, ⚙ del micrófono → **Filtros**, y añadir en este
orden:

1. **Supresión de ruido**, método RNNoise.
2. **Compresor**: relación `3:1`, umbral `−18 dB`.
3. **Limitador**: umbral `−1 dB`.

En ⚙ → **Propiedades avanzadas de audio**, marcar **Mono** si el micrófono
suena solo por un lado.

### 5. Probar el audio

Hablar como en la grabación y mirar la barra del micrófono en el mezclador: no
debe llegar al rojo. Si llega, bajar la ganancia del micrófono, no el
deslizador de OBS. Grabar 10 segundos, escuchar con audífonos y corregir antes
de seguir.

### 6. Grabar

1. Elegir la escena (`Terminal` o `Pantalla completa`).
2. **Iniciar grabación**, esperar 2 segundos en silencio y empezar a hablar.
3. Grabar por partes, una idea por toma. Si algo sale mal, quedarse callado 2
   segundos y repetir la frase: el corte se hace en Canva.
4. Para cambiar de escena o escribir una contraseña, **Pausar**; para terminar,
   2 segundos de silencio y **Detener grabación**.
5. Revisar la grabación antes de desmontar todo: que se oiga y que la letra se lea.

## Tutorial de Canva

La [plantilla del curso](https://canva.link/ensf5pnoj7t3sv9) ya trae la intro
y el cierre. Lo único que se hace en cada video es poner la grabación de OBS en
medio y quitar los errores.

### 1. Crear el diseño del video

1. Abrir el enlace de la plantilla con la cuenta de Canva y elegir **Usar
   plantilla**. Canva crea una copia en la cuenta; la plantilla original no se
   toca.
2. Cambiar el nombre del diseño (arriba, junto al menú **Archivo**) por el del
   video sin extensión, por ejemplo `m01-ssh-es`.

### 2. Subir la grabación

1. En el panel de la izquierda, **Subidos → Subir archivos** y elegir las
   grabaciones de OBS (`~/Videos/apolo-training/crudos/`).
2. Esperar a que terminen de subir y de procesarse.

### 3. Poner la grabación entre la intro y el cierre

1. Abrir la línea de tiempo (abajo) para ver las páginas: la intro al
   principio y el cierre al final.
2. Si la plantilla trae una página vacía en medio, seleccionarla. Si no,
   pasar el cursor entre la intro y el cierre y pulsar **+** para añadir una.
3. Arrastrar la grabación desde **Subidos** a esa página. Clic derecho sobre el
   video → **Establecer video como fondo**, para que ocupe toda la página.
4. Si hay varias tomas, cada una va en su propia página, en orden, siempre
   entre la intro y el cierre.

La intro y el cierre no se mueven ni se cambian.

### 4. Quitar errores y silencios

En la línea de tiempo:

- **Recortar el inicio o el final de una toma:** seleccionar el video y
  arrastrar sus bordes.
- **Quitar un trozo del medio:** llevar el cabezal al inicio del trozo, clic
  derecho → **Dividir**; repetir al final del trozo, seleccionar el trozo del
  medio y **Supr**.
- **Algo sensible que no se puede cortar:** taparlo con un rectángulo de
  **Elementos** solo durante el tiempo en que aparece.

Reproducir el video completo antes de descargarlo: que no haya saltos en mitad
de una palabra y que dure 5 minutos o menos.

### 5. Descargar

1. **Compartir → Descargar**.
2. Tipo de archivo **Video MP4**, calidad **1080p**.
3. **Descargar** y cambiar el nombre del archivo por el de la tabla de
   [Nombres de los archivos](#nombres-de-los-archivos), por ejemplo
   `m01-ssh-es.mp4`.

## Video de prueba

Antes de grabar los videos del curso, cada uno graba un video de prueba de 1
minuto con el micrófono del curso, y Juan lo aprueba.

**Qué tiene:** unos 50 segundos en la escena `Terminal` con `pwd`, `ls -l` y
`cd ~` narrados, montados en la plantilla de Canva. Se descarga como
`m00-prueba-es.mp4`.

**Lo que revisa Juan:**

- [ ] Voz clara, sin eco, sin ruido de fondo ni golpes en las «p».
- [ ] La letra de la terminal se lee bien en una pantalla de portátil.
- [ ] Intro y cierre de la plantilla, sin cambios.
- [ ] Cortes limpios, sin saltos en mitad de una palabra.
- [ ] Nada sensible en pantalla.

La aprobación queda como comentario en la nota de la tarea en Affine, con el
enlace al video (que vive fuera del repo).

## Antes de entregar un video

- [ ] Nombre según la tabla de [Nombres de los archivos](#nombres-de-los-archivos).
- [ ] Grabado con el micrófono del curso.
- [ ] Intro y cierre de la plantilla de Canva, sin cambios.
- [ ] 5 minutos o menos.
- [ ] Nada sensible en pantalla: contraseñas, correos, IPs, nombres internos o
      sesiones ajenas.
- [ ] VTT en español e inglés revisados por una persona.
- [ ] Subido y visible en la plataforma en los dos idiomas.
