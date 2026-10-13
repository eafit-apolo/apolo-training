#!/usr/bin/env python3
"""
pi.py — programa de práctica del curso de inducción de Apolo.

Estima pi lanzando puntos al azar en un cuadrado de lado 1 y contando cuántos
caen dentro del cuarto de círculo (esa proporción se acerca a pi/4).

  python3 pi.py simple   PUNTOS            genera todos los puntos de una vez
  python3 pi.py paralelo PUNTOS PROCESOS   reparte los puntos por lotes entre procesos
"""

import math
import os
import socket
import sys
import time
from multiprocessing import Pool

import numpy as np  # no está en el Python del sistema: hay que cargar el módulo

LOTE = 10_000_000  # puntos por lote en modo paralelo (unos 170 MB por proceso)


def contar(n):
    """Cuántos de n puntos al azar caen dentro del cuarto de círculo."""
    rng = np.random.default_rng()
    x = rng.random(n)
    y = rng.random(n)
    x *= x
    y *= y
    x += y
    return int(np.count_nonzero(x <= 1.0))


def contar_por_lotes(n):
    dentro = 0
    while n > 0:
        m = min(n, LOTE)
        dentro += contar(m)
        n -= m
    return dentro


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("simple", "paralelo"):
        sys.exit(__doc__)
    modo, puntos = sys.argv[1], int(sys.argv[2])
    procesos = int(sys.argv[3]) if modo == "paralelo" and len(sys.argv) > 3 else 1
    nucleos = len(os.sched_getaffinity(0))  # núcleos que Slurm le asignó a este trabajo

    print(
        f"Nodo: {socket.gethostname()} | núcleos disponibles: {nucleos} | procesos: {procesos}",
        flush=True,
    )
    if procesos > nucleos:
        print(
            "Aviso: hay más procesos que núcleos; van a competir entre sí.", flush=True
        )
    elif procesos < nucleos:
        print(
            f"Aviso: tienes {nucleos} núcleos y usas {procesos}; el resto queda ocioso.",
            flush=True,
        )

    inicio = time.time()
    if modo == "simple":
        print(
            f"Este modo necesita unos {puntos * 17 / 1e9:.1f} GB de memoria.",
            flush=True,
        )
        dentro = contar(puntos)
    else:
        reparto = [puntos // procesos] * procesos
        reparto[0] += puntos % procesos
        with Pool(procesos) as pool:
            dentro = sum(pool.map(contar_por_lotes, reparto))

    estimado = 4 * dentro / puntos
    print(
        f"pi ≈ {estimado:.6f} (error {abs(estimado - math.pi):.1e}) en {time.time() - inicio:.1f} s",
        flush=True,
    )


if __name__ == "__main__":
    main()
