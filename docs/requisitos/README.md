# Requisitos de los clústeres (A-03)

Resultados de las pruebas del 5 de octubre de 2026 en Apolo II y Apolo III. Sirven para saber qué puede asumir el curso en cada clúster y qué no. Solo se usaron comandos de lectura y trabajos propios; no se tocó la configuración de ningún clúster.

## Resumen

| Aspecto                          | Apolo II                   | Apolo III                                   |
| -------------------------------- | -------------------------- | ------------------------------------------- |
| Slurm                            | 25.11.4                    | 24.11.5                                     |
| TaskPlugin                       | task/cgroup, task/affinity | solo task/affinity                          |
| JobAcctGatherType                | jobacct_gather/linux       | (null)                                      |
| Partición por defecto            | longjobs                   | ninguna: `srun` sin `-p` falla              |
| Límite de memoria                | Sí: OOM con `--mem=1G`     | No: un trabajo usó 2G con `--mem=1G`        |
| Confinamiento de núcleos         | Sí: `taskset` sigue en 2   | No: `taskset` ve 64                         |
| `TotalCPU` y `MaxRSS` en `sacct` | Sí (`TotalCPU` 00:19.902)  | Vacíos; `Elapsed` y `CPUTime` sí            |
| `sacct` para usuarios normales   | Sí                         | Sí                                          |
| Valores por defecto              | No se registraron          | `DefaultTime` 02:00:00, `DefMemPerCPU` 7500 |
| Python del sistema               | 3.9.25 y 3.11.13           | 3.9.21 y 3.11.9                             |
| numpy en el Python del sistema   | Ausente                    | Ausente                                     |

En Apolo III el `cgroup.conf` no se aplica porque el plugin `task/cgroup` no está activo. Por eso no hay límite de memoria ni confinamiento de núcleos.

## Qué implica para el curso

- **Verificador:** sigue usando `sacct`, con ajustes (V-09). En Apolo II el contador de JobID se reinició, así que se consulta con `sacct -D -j JOBID -u $USER` o filtrando por fecha. En Apolo III no se puede depender de `TotalCPU` ni de `MaxRSS`; se usan `Elapsed` y `CPUTime`.
- **Laboratorios de memoria y núcleos:** se practican en la VM de práctica, donde sí hay cgroups. La lección debe explicar que Apolo III hoy no aplica esos límites.
- **Ejemplos de comandos:** llevan `-p` explícito, porque Apolo III no tiene partición por defecto (A-04).
- **numpy:** el candidato común es `py3-numpy/1.26.4` (OpenHPC, Python 3.11). Tiene el mismo nombre en los dos clústeres y funciona en el login y en los nodos. `miniconda3` (25.5.1 y 25.11.1) no trae numpy. Pendiente de decisión (I-07).
- **Particiones:** en Apolo II, `longjobs-smt` no aparece en `sinfo` para un usuario normal (P-02).

## Observaciones

En Apolo II, dos nodos (`nodo-A` y `nodo-C` en las salidas) rechazaron trabajos con `Job credential expired`, posiblemente por un desfase de reloj. El segundo intento corrió en otros nodos sin ese error. Los nombres reales de los nodos se reemplazaron por letras.

## Archivos

| Archivo                                  | Contenido                                                         |
| ---------------------------------------- | ----------------------------------------------------------------- |
| `apolo2.txt`                             | Pruebas completas en Apolo II                                     |
| `apolo2-intento1-credential-expired.txt` | Primer intento en Apolo II, con el error `Job credential expired` |
| `apolo3.txt`                             | Pruebas completas en Apolo III                                    |
