# content

Contenido del curso: módulos, lecciones y quices en Markdown, en español
(`es/`) y luego en inglés (`en/`). Lo carga en la base de datos el importador
de la API (B-04). Los videos no van al repo: se suben desde el panel de
instructor.

- [`mapa.md`](mapa.md): qué enseña cada módulo, sus videos, prácticas y
  preguntas. Si algo cambia, se cambia primero ahí.
- [`glosario.md`](glosario.md): traducción fija de los términos ES → EN.
- [`es/_plantilla.md`](es/_plantilla.md) y
  [`es/_plantilla-modulo.md`](es/_plantilla-modulo.md): de dónde se copia cada
  lección y cada módulo.
- [`schema/`](schema/): los esquemas del front matter. El importador rechaza un
  archivo que no los cumpla.

## Estructura

```text
content/
├── mapa.md
├── glosario.md
├── schema/
│   ├── leccion.schema.json
│   └── modulo.schema.json
├── es/
│   ├── _curso.md
│   ├── _plantilla.md
│   ├── _plantilla-modulo.md
│   ├── m00/
│   │   ├── _modulo.md
│   │   └── bienvenida.md
│   ├── m01/
│   │   ├── _modulo.md
│   │   ├── vpn.md
│   │   └── ssh.md
│   └── …
└── en/          (fase 2: mismas rutas, mismos id y claves)
```

- `es/_curso.md` tiene los datos del curso ([esquema](schema/curso.schema.json)):
  `id` (su dirección en la plataforma, `induccion`), `titulo` y `descripcion`.
- Cada módulo es una carpeta `mNN/` con su `_modulo.md` y una lección por
  archivo.
- La ruta de una lección es su `id`: `es/m05/trabajos.md` tiene
  `id: m05/trabajos`, que es también su dirección en la plataforma.
- El importador lee `_curso.md` y las carpetas `mNN/`. Las plantillas están
  fuera, así que no se importan, pero sí se validan.

## Una lección

Arriba, el front matter con los datos ([esquema](schema/leccion.schema.json)):

| Campo        | Obligatorio | Qué es                                                                      |
| ------------ | ----------- | --------------------------------------------------------------------------- |
| `id`         | sí          | `mNN/slug`, igual a la ruta del archivo.                                    |
| `titulo`     | sí          | Título de la lección.                                                       |
| `orden`      | sí          | Posición dentro del módulo, desde 1.                                        |
| `duracion`   | sí          | Minutos de la lección completa.                                             |
| `video`      | no          | Clave del video (`m05-trabajos`), o una por sistema operativo en la de VPN. |
| `practicas`  | no          | Prácticas de la VM, con el nombre del verificador.                          |
| `quiz`       | no          | Preguntas, con sus opciones y la explicación.                               |
| `quiz_final` | no          | `true` solo en el quiz final del curso.                                     |

Una lección no tiene un `tipo`: la plataforma muestra lo que trae (video,
texto, prácticas, quiz) y la da por completa cuando se cumple todo
(`docs/diseno/modelo-datos.md`).

Debajo, el texto, siempre con estas secciones `##` y en este orden:

1. **Objetivos.**
2. **Resumen:** los comandos del video.
3. **Práctica:** solo si la lección tiene prácticas. Pasos numerados que
   terminan en `apolo-training verificar <práctica>`.
4. **Si algo falla:** los errores que de verdad aparecen y qué hacer.

El video (arriba) y el quiz (al final) no se escriben en el texto: los pone la
plataforma a partir del front matter.

## Convenciones

- **Comandos** en bloques `bash`, sin el `$` del prompt. Las salidas, en
  bloques `text`.
- **Valores a reemplazar** entre `<ángulos>`: `ssh <usuario>@…`,
  `sbatch -p <partición> …`.
- **En Slurm, siempre `-p <partición>`:** Apolo III no tiene partición por
  defecto.
- **Pestañas Apolo II / Apolo III** solo donde algo cambia, con un bloque
  `::: apolo2` y otro `::: apolo3` seguidos. La plataforma los muestra como
  pestañas y abre la del clúster del usuario; en GitHub se leen como texto.

  ```markdown
  ::: apolo2

  La partición por defecto es `longjobs`.

  :::

  ::: apolo3

  No hay partición por defecto.

  :::
  ```

- **Se tutea** al usuario: «Entra a la carpeta…», como en los `LEEME.txt` de
  `labs/`.
- **Términos** del [glosario](glosario.md); si falta uno, se agrega en el mismo
  PR.
- **Sin datos reales:** ni usuarios, ni IPs, ni nombres internos de nodos o
  servidores. El repo es público.

## Importar y validar

El importador es de la API (B-04), desde `api/`:

```bash
python -m app.importar --revisar    # solo valida, como el job content del CI
python -m app.importar              # valida y carga en la base
```

En el entorno de desarrollo lo corre el servicio `migrar`; después de editar
algo, `docker compose -f deploy/compose.dev.yaml run --rm migrar` lo vuelve a
cargar. Cada error dice el archivo y el campo.

## Lo que revisa el importador además del esquema

- El `id` coincide con la ruta del archivo y con la carpeta del módulo.
- No hay dos lecciones con el mismo `orden` en un módulo.
- Las `clave` de las preguntas son únicas en todo el curso y empiezan por el
  módulo de la lección (`m05-…` en `m05/`).
- Las carpetas de `es/` se llaman `mNN`, cada una con su `_modulo.md` y al
  menos una lección.
- Con `en/` (fase 2): cada archivo tiene su par en `es/` con el mismo `id`, las
  mismas `clave` de preguntas y las mismas opciones correctas, en el mismo
  orden. Los datos que no se traducen (`orden`, `duracion`, `video`,
  `practicas`, `quiz_final`) son iguales a los de `es/`. Si falta el inglés, la
  plataforma muestra el español.

Cambiar el texto de una pregunta no cambia su `clave`, así que los intentos
anteriores se conservan. Cambiar la `clave` crea una pregunta nueva.
