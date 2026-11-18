---
id: m02/terminal
titulo: Comandos básicos de Linux
orden: 1
duracion: 10
video: m02-terminal
practicas: [terminal]
quiz:
  # ─── Pregunta 1: qué hace rm ───────────────────────────────────────────────

  - clave: m02-rm
    enunciado: >-
      Borraste por error `resultados.csv` con `rm`. ¿Cómo lo recuperas?

    opciones:
      # Correcta
      - texto: >-
          No se puede desde la terminal: `rm` no tiene papelera y el archivo ya
          no está.
        correcta: true

      # Incorrecta
      - texto: Lo saco de la papelera con `mv`.

      # Incorrecta
      - texto: Pulso Ctrl+Z para deshacer.

    explicacion: >-
      `rm` borra para siempre: en la terminal no hay papelera ni forma de
      deshacer. Ctrl+Z tampoco deshace: deja en pausa el programa que está
      corriendo. Antes de borrar, revisa con `ls` qué vas a borrar, sobre todo
      con `rm -r`, que borra una carpeta con todo lo que tiene.

  # ─── Pregunta 2: cómo salir de nano guardando ──────────────────────────────

  - clave: m02-nano
    enunciado: >-
      Escribiste la clave en `respuesta.txt` con `nano`. ¿Cómo guardas y sales?

    opciones:
      # Correcta
      - texto: >-
          Ctrl+X, respondo que sí quiero guardar y pulso Enter para dejar el
          nombre.
        correcta: true

      # Incorrecta
      - texto: Escribo `:wq` y pulso Enter.

      # Incorrecta
      - texto: Cierro la ventana de la terminal; nano guarda solo.

    explicacion: >-
      En la barra de abajo de nano, `^` quiere decir Ctrl. Ctrl+X sale y, si
      hay cambios, pregunta si los guardas: `Y` (_yes_), o `S` si nano está en
      español, y Enter para dejar el nombre del archivo. Ctrl+O guarda sin salir. `:wq` es de otro editor,
      vim. Si cierras la ventana, se corta la conexión y pierdes lo que no
      guardaste.
---

## Objetivos

Al terminar podrás:

- Saber en qué carpeta estás y moverte entre carpetas.
- Crear, copiar, mover y borrar archivos y carpetas.
- Leer un archivo, buscar texto con `grep` y editarlo con `nano`.
- Guardar en un archivo lo que imprime un comando.

## Resumen

### 1. Dónde estás y qué hay

```bash
pwd       # en qué carpeta estás
ls        # qué hay en ella
ls -l     # lo mismo, con detalles
```

Al entrar, siempre estás en tu carpeta personal, `/home/<usuario>`. Con `ls -l`
cada línea es un archivo o una carpeta:

```text
drwxr-xr-x. 4 <usuario> <grupo> 4096 Nov 18 10:15 datos
-rw-r--r--. 1 <usuario> <grupo>  847 Nov 18 10:12 LEEME.txt
```

- La primera letra dice qué es: `d`, una carpeta; `-`, un archivo.
- Las otras nueve son los permisos, en tres grupos: lo que puedes hacer tú, tu
  grupo y los demás usuarios. `r` es leer; `w`, escribir; `x`, ejecutar un
  programa o entrar a una carpeta. Aquí solo hace falta saber leerlos: los
  trabajos de Slurm no necesitan que les cambies los permisos.
- Después vienen el dueño, el grupo, el tamaño en bytes, la fecha y el nombre.

### 2. Moverte entre carpetas

```bash
cd <carpeta>      # entra a una carpeta
cd ..             # sube a la carpeta de arriba
cd ~              # vuelve a tu carpeta personal (cd solo hace lo mismo)
cd ~/<carpeta>    # entra a una carpeta dentro de tu carpeta personal
```

`~` es tu carpeta personal y `..`, la carpeta de arriba. Las mayúsculas
importan: `Datos` y `datos` son dos nombres distintos. Escribe las primeras
letras de un nombre y pulsa Tab: la terminal completa el resto.

### 3. Crear, copiar, mover y borrar

```bash
mkdir <carpeta>                    # crea una carpeta
cp <archivo> <copia>               # copia un archivo
cp -r <carpeta> <copia>            # copia una carpeta con todo lo que tiene
mv <archivo> <carpeta>/            # mueve un archivo a otra carpeta
mv <nombre-viejo> <nombre-nuevo>   # le cambia el nombre
rm <archivo>                       # borra un archivo
rm -r <carpeta>                    # borra una carpeta con todo lo que tiene
```

**`rm` no tiene papelera:** lo que borras no se puede recuperar. Antes de
borrar, mira con `ls` qué vas a borrar.

### 4. Leer y buscar

```bash
cat <archivo>                 # muestra el archivo completo
grep <texto> <archivo>        # muestra las líneas que tienen ese texto
grep -r <texto> <carpeta>     # lo busca en todos los archivos de la carpeta
```

`grep -r` dice en qué archivo está cada línea que encuentra:

```text
<carpeta>/<archivo>:<la línea que tiene el texto>
```

### 5. Editar con nano

```bash
nano <archivo>
```

Si el archivo no existe, nano lo crea al guardar. Escribe con normalidad y usa
los atajos de la barra de abajo, donde `^` quiere decir Ctrl:

- **Ctrl+O** y Enter: guarda sin salir.
- **Ctrl+X**: sale. Si hay cambios sin guardar, pregunta si los guardas:
  `Y` para guardar (`S` si nano está en español) o `N` para salir sin guardar,
  y después Enter para dejar el nombre.

### 6. Guardar en un archivo lo que imprime un comando

Con `>`, lo que un comando iba a mostrar en la pantalla queda en un archivo:

```bash
ls -l > lista.txt
echo <texto> > <archivo>
```

Si el archivo ya existe, `>` lo reemplaza completo.

## Práctica

En la VM de práctica (`apolo-training.apolo.eafit.edu.co`):

1. Copia el material del curso a tu carpeta personal. Se hace una sola vez y
   deja lista también la práctica del módulo 3:

   ```bash
   apolo-training preparar
   ```

   ```text
   Listo: el material del curso quedó en ~/apolo-training
   Generé ~/apolo-training/archivos/ida.txt con tu código para la práctica de archivos.
   ```

2. Entra a la carpeta de esta práctica y lee las instrucciones:

   ```bash
   cd ~/apolo-training/terminal
   cat LEEME.txt
   ```

3. Recorre la carpeta `datos/` con `cd`, `ls` y `cat`. En uno de los archivos
   hay una línea con la clave del curso, que empieza por `TRN-`.
4. Búscala en todos a la vez, sin abrir archivo por archivo:

   ```bash
   grep -r TRN- datos/
   ```

5. Guarda la clave en `respuesta.txt`, dentro de `~/apolo-training/terminal`.
   Con `nano respuesta.txt`, o en una sola línea:

   ```bash
   echo <clave> > respuesta.txt
   ```

6. Verifica:

   ```bash
   apolo-training verificar terminal
   ```

## Si algo falla

- **`apolo-training: command not found`:** carga el verificador con
  `module load apolo-training` y vuelve a correr el comando.
- **`cd: <carpeta>: No such file or directory`:** el nombre está mal escrito o
  la carpeta no está donde estás. Revisa con `pwd` y `ls`, y fíjate en las
  mayúsculas. En español, el mensaje termina en
  `No existe el fichero o el directorio`.
- **`cp: -r not specified; omitting directory '<carpeta>'`:** para copiar una
  carpeta hace falta `cp -r`.
- **`rm: cannot remove '<carpeta>': Is a directory`:** para borrar una carpeta
  hace falta `rm -r`. Revisa antes con `ls` lo que tiene. En español:
  `rm: no se puede borrar '<carpeta>': Es un directorio`.
- **Un comando se queda esperando y no vuelve el prompt:** por ejemplo,
  `grep TRN-` sin la carpeta al final espera que escribas el texto. Pulsa
  Ctrl+C y corrígelo.
- **`No encuentro ~/apolo-training. Primero corre: apolo-training preparar`:**
  corre `apolo-training preparar`. Si ya lo habías corrido, vuelve a hacerlo:
  restaura lo que falte sin tocar tus archivos.
- **`Aún no veo ~/apolo-training/terminal/respuesta.txt`:** guardaste el
  archivo en otra carpeta o con otro nombre. Entra con
  `cd ~/apolo-training/terminal` y guárdalo de nuevo.
- **`… no tiene la clave correcta`:** revisa con `cat respuesta.txt` que la
  clave esté completa: `TRN-` y dos grupos de cuatro letras o números.

¿Sigue sin funcionar? Escribe a `apolo@eafit.edu.co` con tu usuario, el comando
que corriste y el mensaje de error.
