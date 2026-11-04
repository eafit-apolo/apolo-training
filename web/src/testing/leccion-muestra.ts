// La lección de muestra de la F-04 (DoD 1): `m05/trabajos` en español y en
// inglés, con todo lo que puede traer una lección (pestañas, comandos, salidas,
// una tabla y pasos con código). Sale de content/es/_plantilla.md sin los
// comentarios; el inglés usa content/glosario.md.

export const MUESTRA_ES = `## Objetivos

Al terminar podrás:

- Enviar un trabajo a Slurm con \`sbatch\` y seguirlo con \`squeue\`.
- Leer los estados de la cola y la razón de espera.
- Revisar con \`sacct\` cómo terminó un trabajo.

## Resumen

Un trabajo es un script con directivas \`#SBATCH\` al inicio:

\`\`\`bash
#!/bin/bash
#SBATCH --job-name=<nombre>
#SBATCH --partition=<partición>
#SBATCH --mem=1G
#SBATCH --time=00:10:00

python3 <programa>.py
\`\`\`

Envíalo y síguelo:

\`\`\`bash
sbatch <script>.sh
squeue -u $USER
sacct -j <JobID>
\`\`\`

\`\`\`text
JOBID  PARTITION  NAME      USER     ST  TIME  NODES  NODELIST(REASON)
1234   <part>     <nombre>  <user>   PD  0:00  1      (Priority)
\`\`\`

| Estado | Qué significa      |
| ------ | ------------------ |
| \`PD\`   | Espera en la cola  |
| \`R\`    | Está corriendo     |

::: apolo2

La partición por defecto es \`longjobs\` (hasta 14 días). También están \`bigmem\`,
\`accel\`, \`accel-2\` y \`learning\`. Aun así, escribe siempre \`-p <partición>\`.

:::

::: apolo3

No hay partición por defecto: sin \`-p <partición>\`, \`sbatch\` falla. Las
particiones son \`bigmem\`, \`longjobs\` y \`accel\`.

:::

## Práctica

En la VM de práctica (\`apolo-training.apolo.eafit.edu.co\`):

1. Entra a la carpeta del curso y abre el script:

   \`\`\`bash
   cd ~/apolo-training
   nano curso.sh
   \`\`\`

2. Envía el trabajo:

   \`\`\`bash
   sbatch -p <partición> curso.sh
   \`\`\`

3. Verifica:

   \`\`\`bash
   apolo-training verificar memoria
   \`\`\`

## Si algo falla

- **\`sbatch: error: invalid partition specified\`:** la partición no existe en
  tu clúster. Revisa el nombre con \`sinfo\`.

¿Sigue sin funcionar? Escribe a \`apolo@eafit.edu.co\` con tu usuario, el JobID,
el comando y el mensaje de error.
`;

export const MUESTRA_EN = `## Objectives

When you finish you will be able to:

- Submit a job to Slurm with \`sbatch\` and follow it with \`squeue\`.
- Read the queue states and the reason a job waits.
- Check with \`sacct\` how a job ended.

## Summary

A job is a script with \`#SBATCH\` directives at the top:

\`\`\`bash
#!/bin/bash
#SBATCH --job-name=<name>
#SBATCH --partition=<partition>
#SBATCH --mem=1G
#SBATCH --time=00:10:00

python3 <program>.py
\`\`\`

Submit it and follow it:

\`\`\`bash
sbatch <script>.sh
squeue -u $USER
sacct -j <JobID>
\`\`\`

\`\`\`text
JOBID  PARTITION  NAME    USER    ST  TIME  NODES  NODELIST(REASON)
1234   <part>     <name>  <user>  PD  0:00  1      (Priority)
\`\`\`

| State | What it means       |
| ----- | ------------------- |
| \`PD\`  | Waiting in the queue |
| \`R\`   | Running             |

::: apolo2

The default partition is \`longjobs\` (up to 14 days). There are also \`bigmem\`,
\`accel\`, \`accel-2\` and \`learning\`. Even so, always write \`-p <partition>\`.

:::

::: apolo3

There is no default partition: without \`-p <partition>\`, \`sbatch\` fails. The
partitions are \`bigmem\`, \`longjobs\` and \`accel\`.

:::

## Practice

On the practice VM (\`apolo-training.apolo.eafit.edu.co\`):

1. Go to the course folder and open the script:

   \`\`\`bash
   cd ~/apolo-training
   nano curso.sh
   \`\`\`

2. Submit the job:

   \`\`\`bash
   sbatch -p <partition> curso.sh
   \`\`\`

3. Check it:

   \`\`\`bash
   apolo-training verificar memoria
   \`\`\`

## If something goes wrong

- **\`sbatch: error: invalid partition specified\`:** the partition doesn't exist
  on your cluster. Check the name with \`sinfo\`.

Still not working? Write to \`apolo@eafit.edu.co\` with your username, the JobID,
the command and the error message.
`;

/** Lo que nunca debe ejecutarse (DoD 3). */
export const MUESTRA_PELIGROSA = `## Objetivos

Hola <script>window.__atacado = true</script> y <img src="x" onerror="window.__atacado = true">.

<div onclick="window.__atacado = true">Un bloque HTML</div>

[Un enlace malo](javascript:window.__atacado=true) y [uno bueno](https://apolo-docs.readthedocs.io).
`;
