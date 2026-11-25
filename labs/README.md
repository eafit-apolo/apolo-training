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

## Medido en la VM de práctica (V-03, 25-nov-2026)

Con un usuario `apolo2` en la partición `learning`, la VM sin otros trabajos y
el verificador del repositorio. Las siete prácticas dieron `[APROBADO]`.

| Práctica   | Última línea de `curso.sh`            | Núcleos | `--mem` | Resultado                                          | Duración | Eficiencia | Memoria máxima |
| ---------- | ------------------------------------- | ------: | ------- | -------------------------------------------------- | -------: | ---------: | -------------: |
| `modulos`  | `python3 pi.py simple 1000000`        |       1 | 1G      | `FAILED` sin el módulo (`ModuleNotFoundError`)     |      1 s |          — |           5 MB |
| `modulos`  | igual, con `module load`              |       1 | 1G      | `COMPLETED`                                        |      1 s |          — |          35 MB |
| `memoria`  | `python3 pi.py simple 100000000`      |       1 | 1G      | `OUT_OF_MEMORY` (`0:125`, `oom_kill` en el `.out`) |    < 1 s |          — |       1 025 MB |
| `memoria`  | igual                                 |       1 | 4G      | `COMPLETED`                                        |      2 s |       70 % |       1 642 MB |
| `nucleos`  | `python3 pi.py paralelo 3800000000 1` |       4 | 1G      | `COMPLETED`                                        |     45 s |       25 % |         185 MB |
| `paralelo` | `python3 pi.py paralelo 3800000000 4` |       4 | 1G      | `COMPLETED`                                        |     13 s |       94 % |         680 MB |

- **PUNTOS de los laboratorios de núcleos y paralelo: 3 800 000 000.** Con un
  proceso, un núcleo de la VM cuenta unos 83 millones de puntos por segundo
  (1 000 millones en 12 s), así que el laboratorio de núcleos dura unos 45 s
  (entre 30 y 60 s, como pide el mapa). Si cambia la VM, se repite la medición.
- **Esos dos laboratorios usan el modo `paralelo`**, también con un solo
  proceso: el modo `simple` guarda todos los puntos a la vez (17 bytes por
  punto) y para durar 30 s necesitaría más de 40 GB, mucho más de lo que deja
  la QOS `curso` (5 GB). Con `paralelo`, cada proceso usa unos 190 MB y los
  cuatro caben en el `--mem=1G` de `curso.sh`.
- **Un trabajo de 4 núcleos ocupa la VM entera** (tiene 4): si varios usuarios
  los envían a la vez, corren de uno en uno y los demás esperan en `PD`.
- La tercera copia de un trabajo queda en `PD` con `(QOSMaxJobsPerUserLimit)`:
  la QOS deja dos a la vez por usuario (módulo 5).

## Pendiente

- `curso.sh` todavía tiene el marcador de la partición de práctica
  (`<particion-curso>`): lo reemplaza la P-04 con la de cada perfil. La línea
  del módulo con numpy ya es `py3-numpy/1.26.4` (I-07), comentada: el
  laboratorio de módulos pide descomentarla.
