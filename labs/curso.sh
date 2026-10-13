#!/bin/bash
#SBATCH --job-name=curso-modulos         # cambia el nombre en cada laboratorio
#SBATCH --partition=<particion-curso>    # partición de práctica de tu clúster
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1                # laboratorios de núcleos y paralelo: 4
#SBATCH --mem=1G                         # laboratorio de memoria: empieza en 1G
#SBATCH --time=00:10:00
#SBATCH --output=%x-%j.out               # queda como nombre-del-trabajo-JobID.out

# module load <python-con-numpy>         # laboratorio de módulos: descomenta esta línea

python3 pi.py simple 1000000
