# labs

Material de las prácticas del curso. `apolo-training preparar` copia esta
carpeta (menos este README) a `~/apolo-training` de cada usuario y genera
`archivos/ida.txt` con un código propio.

| Ruta                | Práctica                                    | Qué hace el usuario                                                                                |
| ------------------- | ------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `terminal/`         | `terminal`                                  | Busca la clave `TRN-…` en `datos/` con `cd`, `ls`, `cat` y `grep`, y la guarda en `respuesta.txt`. |
| `archivos/`         | `archivos`                                  | Descarga `ida.txt`, le cambia el nombre a `vuelta.txt` y lo sube.                                  |
| `pi.py`, `curso.sh` | `modulos`, `memoria`, `nucleos`, `paralelo` | Edita `curso.sh` y lo envía con `sbatch`.                                                          |

## Reglas para quien cambie el material

- En `terminal/datos/` debe haber **exactamente una** clave con el formato
  `TRN-XXXX-XXXX`: el verificador la toma de aquí y las pruebas lo comprueban.
- No se agrega `archivos/ida.txt`: lo genera `preparar` para cada usuario.
- Nada de IPs, hosts internos ni datos reales de usuarios (el repositorio será
  público).

## Pendiente

- `curso.sh` tiene dos marcadores que se reemplazan cuando se decidan: la
  partición de práctica (`<particion-curso>`) y la línea del módulo con numpy
  (`<python-con-numpy>`, I-07). Se calibran en la V-03.
