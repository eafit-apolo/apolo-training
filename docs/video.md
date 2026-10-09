# Guía de grabación de videos (M-01)

Cómo se graban, editan y exportan los videos del curso para que todos salgan con
la misma calidad y el mismo estilo, los grabe quien los grabe. Los videos que
hay que hacer, su duración y quién graba cada uno están en
[`content/mapa.md`](../content/mapa.md).

Cada uno configura OBS y Kdenlive en su propio computador siguiendo los
tutoriales de abajo; no se comparten archivos de configuración. Los videos nunca
entran al repo: `.gitignore` ya excluye `*.mp4`, `*.mkv`, `*.mov` y `*.webm`.

## Resumen

| Qué            | Valor                                                           |
| -------------- | --------------------------------------------------------------- |
| Grabación      | OBS Studio, 1920×1080 a 30 fps, MKV o MP4 fragmentado           |
| Escenas        | `Pantalla completa` y `Terminal`                                |
| Terminal       | Fuente monoespaciada de 18 pt o más, tema de alto contraste     |
| Audio          | El mismo micrófono para todos, 48 kHz, sala sin eco, sin música |
| Intro y cierre | `intro.mp4` y `cierre.mp4`, 5 s cada uno, iguales en todos      |
| Edición        | Kdenlive, perfil HD 1080p 30 fps                                |
| Archivo final  | MP4 con H.264 + AAC, audio a −16 LUFS (±1), 5 minutos o menos   |
| Nombre         | `mNN-<lección>-es.mp4`, por ejemplo `m01-ssh-es.mp4`            |
| Subtítulos     | `mNN-<lección>-es.vtt` y `mNN-<lección>-en.vtt`                 |

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

- **Intro y cierre iguales en todos los videos**, al estilo de Platzi o
  Coursera: una animación corta de marca que no menciona el módulo ni el tema y
  no se edita nunca.
  - `intro.mp4` (5 s): los logos del centro y de la universidad y «Curso de
    inducción Apolo».
  - `cierre.mp4` (5 s): los logos y «Centro de Computación Científica Apolo ·
    Universidad EAFIT».
  - Los dos son 1920×1080 a 30 fps, sin sonido, empiezan y terminan en negro.
  - Se guardan en la carpeta compartida del equipo, no en el repo. Cada uno los
    copia a `~/Videos/apolo-training/`.
- **El tema del video lo dice la voz**, en la primera frase después de la
  intro: «En este video vas a…».
- **Sin música de fondo** en ningún momento: distrae y trae problemas de
  licencia.
- **Se habla de tú**, en frases cortas, a unas 130 palabras por minuto. Un video
  de 5 minutos son unas 650 palabras de guion.
- **Los comandos se escriben en vivo**, despacio, y después de cada uno se deja
  1 o 2 segundos para leer la salida antes de hablar de ella.
- **Lo que se dice coincide con el resumen** de la lección: los mismos comandos
  y en el mismo orden.

## Antes de grabar

### Sala y micrófono

- **Un solo micrófono para todos.** El centro no tiene uno, así que hay que
  conseguir un micrófono externo (USB o de solapa) antes de grabar, y todos los
  videos se graban con ese mismo. Así el audio suena igual en todo el curso. No
  se usa el micrófono del portátil ni el de unos audífonos.
- Micrófono a 10 o 20 cm de la boca, un poco de lado para que no le peguen las
  «p» y las «b».
- Sala pequeña, con puerta y ventanas cerradas. El aire acondicionado no se
  puede apagar, pero no hace ruido; si se oye en la prueba de nivel, el filtro
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
   - Calidad: **Calidad indistinguible, archivo grande**.
   - Formato: **MKV** o **MP4 fragmentado**.
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

### 5. Probar el nivel

Hablar como en la grabación y mirar la barra del micrófono: los picos deben
quedar en la zona amarilla, entre −12 y −6 dB. Si llegan al rojo, bajar la
ganancia del micrófono, no el deslizador de OBS. Grabar 10 segundos, escuchar
con audífonos y corregir antes de seguir.

### 6. Grabar

1. Elegir la escena (`Terminal` o `Pantalla completa`).
2. **Iniciar grabación**, esperar 2 segundos en silencio y empezar a hablar.
3. Grabar por partes, una idea por toma. Si algo sale mal, quedarse callado 2
   segundos y repetir la frase: el corte se hace en la edición.
4. Para cambiar de escena o escribir una contraseña, **Pausar**; para terminar,
   2 segundos de silencio y **Detener grabación**.
5. Revisar la grabación antes de desmontar todo: que se oiga y que la letra se lea.

## Tutorial de Kdenlive

Escrito para Kdenlive 24 o más reciente. Los nombres de los menús van en
inglés, que es como viene por defecto.

Trabajar siempre fuera del repo, una carpeta por video, por ejemplo
`~/Videos/apolo-training/m01-ssh/`. Kdenlive crea ahí carpetas de proxies y
miniaturas que no deben acabar en git.

### 1. Crear el proyecto base

Se hace una sola vez. El resultado es un proyecto vacío con la intro y el
cierre, que luego se copia para cada video.

1. **Settings → Configure Kdenlive → Project Defaults**: perfil
   **HD 1080p 30 fps** (1920×1080, 30 fps), 1 pista de video y 1 de audio.
   **OK**.
2. **File → New**. Comprobar en **Project → Project Settings** que el perfil
   es el de 1080p 30 fps.
3. Clic derecho en el **Project Bin → Add Clip or Folder** y elegir
   `~/Videos/apolo-training/intro.mp4` y `cierre.mp4`.
4. Arrastrar `intro.mp4` al inicio de la pista V1. `cierre.mp4` se deja en el
   Project Bin y se pone al final de cada video.
5. **Marcador de 5 minutos:** llevar el cursor a `00:04:55:00` y
   **Timeline → Guides → Add/Remove Guide**. Avisa cuando el video se acerca
   al límite.
6. **File → Save As** en `~/Videos/apolo-training/base.kdenlive`.

### 2. Empezar un video

1. **File → Open** `~/Videos/apolo-training/base.kdenlive`.
2. Enseguida, **File → Save As** en la carpeta del video, con el nombre del
   video (`m01-ssh.kdenlive`). Así el proyecto base no se modifica.

La intro y el cierre no se tocan: son los mismos en todos los videos.

### 3. Importar la grabación

1. Clic derecho en el **Project Bin → Add Clip or Folder** y elegir las grabaciones.
   Si Kdenlive pregunta si cambiar el perfil del proyecto, responder **No**: la
   grabación ya es 1080p30.
2. Arrastrar el primer clip a V1, justo después de la intro (en 5 s). El audio
   cae solo en A1.

### 4. Cortar

Atajos básicos:

| Tecla     | Hace                                      |
| --------- | ----------------------------------------- |
| Espacio   | Reproducir y pausar                       |
| J / K / L | Atrás, pausa y adelante (repetir acelera) |
| ← / →     | Un cuadro atrás o adelante                |
| Shift+R   | Cortar el clip en la posición del cursor  |
| Supr      | Borrar el trozo seleccionado              |
| Ctrl+Z    | Deshacer                                  |
| + / −     | Acercar o alejar la línea de tiempo       |

Para quitar un error, un silencio largo o una contraseña:

1. Poner el cursor al inicio del trozo y **Shift+R**.
2. Poner el cursor al final y **Shift+R**.
3. Clic en el trozo del medio y **Supr**.
4. Clic derecho en el hueco que queda → **Remove Space**.

Repetir con cada toma que se quiera quitar. Al final, arrastrar `cierre.mp4`
del Project Bin justo después del último clip.

### 5. Transiciones y tapar datos

- **Entrada y salida suaves:** la intro termina en negro y el cierre empieza
  en negro. En **Effects**, buscar _Fade from Black_ y arrastrarlo al inicio
  del primer clip de la grabación; _Fade to Black_ al final del último. Medio
  segundo basta. No se usan otras transiciones.
- **Tapar algo sensible** que no se pueda cortar: efecto _Obscure_ (pixelar)
  sobre el clip, ajustando el rectángulo en el monitor.

### 6. Revisar el audio

**View → Audio Mixer**. Reproducir el video entero: los picos deben quedar entre
−12 y −6 dB. Si un trozo suena mucho más bajo que el resto, efecto _Volume
(keyframable)_ sobre ese clip. La normalización final a −16 LUFS se hace
después, en el paso 8.

### 7. Exportar

1. **Project → Render** (Ctrl+Enter).
2. Preset **MP4-H264/AAC**.
3. **Output file:** `~/Videos/apolo-training/m01-ssh/m01-ssh-sin-normalizar.mp4`.
4. Rango: **Full project**. Resolución completa.
5. **Render to File** y esperar a que termine.

El preset queda igual para todos; si se cambia, guardarlo como preset propio y
avisar.

### 8. Normalizar el audio a −16 LUFS

Kdenlive no deja el audio exactamente en −16 LUFS, así que se normaliza con
ffmpeg sin volver a codificar el video:

```bash
ffmpeg -i m01-ssh-sin-normalizar.mp4 \
  -c:v copy \
  -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 -c:a aac -b:a 160k \
  -movflags +faststart \
  m01-ssh-es.mp4
```

`-movflags +faststart` hace que el video empiece a reproducirse en la
plataforma antes de descargarse entero.

### 9. Comprobar el archivo final

```bash
# Códec, resolución, cuadros por segundo y duración
ffprobe -v error \
  -show_entries stream=codec_name,width,height,r_frame_rate:format=duration \
  -of compact m01-ssh-es.mp4

# Sonoridad integrada: debe dar entre -17 y -15 LUFS
ffmpeg -hide_banner -nostats -i m01-ssh-es.mp4 \
  -af ebur128=framelog=quiet -f null - 2>&1 | grep -A1 'Integrated loudness'
```

La salida esperada es `h264`, `1920`, `1080`, `30/1`, `aac`, una duración de
300 s o menos y una sonoridad cercana a `-16.0 LUFS`.

## Subtítulos

Los subtítulos son una tarea aparte, pero salen del mismo proyecto:

1. En Kdenlive, el reconocimiento de voz (_Speech Recognition_, con Whisper)
   genera los subtítulos en español en la pista de subtítulos.
2. Revisarlos a mano: nombres de comandos, opciones y rutas casi siempre
   salen mal.
3. Exportarlos en SRT y pasarlos a VTT:

   ```bash
   ffmpeg -i m01-ssh-es.srt m01-ssh-es.vtt
   ```

4. La versión en inglés parte del VTT en español ya revisado, y también la
   revisa una persona.

## Video de prueba

Antes de grabar los videos del curso, cada uno graba un video de prueba de 1
minuto con su equipo y su sala, y Juan lo aprueba.

**Qué tiene:** la intro, unos 50 segundos en la escena `Terminal` con `pwd`,
`ls -l` y `cd ~` narrados, y el cierre. Se exporta como `m00-prueba-es.mp4`
siguiendo esta guía completa, del paso 1 de OBS al paso 9 de Kdenlive.

**Lo que revisa Juan:**

- [ ] 1920×1080 a 30 fps, H.264 + AAC, MP4.
- [ ] Sonoridad entre −17 y −15 LUFS.
- [ ] Voz clara, sin eco, sin ruido de fondo ni golpes en las «p».
- [ ] La letra de la terminal se lee bien en una pantalla de portátil.
- [ ] Con `intro.mp4` y `cierre.mp4` sin cambios.
- [ ] Cortes limpios, sin saltos en mitad de una palabra.
- [ ] Nada sensible en pantalla.

La aprobación queda como comentario en la nota de la tarea en Affine, con el
enlace al video (que vive fuera del repo).

## Antes de entregar un video

Es la DoD de «Videos y subtítulos» de la
[plantilla de PR](../.github/pull_request_template.md), más lo de esta guía:

- [ ] Nombre según la tabla de [Nombres de los archivos](#nombres-de-los-archivos).
- [ ] MP4 H.264/AAC 1080p30, 5 minutos o menos, audio a −16 LUFS (paso 9).
- [ ] Con `intro.mp4` y `cierre.mp4` sin cambios.
- [ ] Nada sensible en pantalla: contraseñas, correos, IPs, nombres internos o
      sesiones ajenas.
- [ ] VTT en español e inglés revisados por una persona.
- [ ] Subido y visible en la plataforma en los dos idiomas.
