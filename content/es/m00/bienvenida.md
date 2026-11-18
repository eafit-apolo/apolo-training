---
id: m00/bienvenida
titulo: Bienvenida
orden: 1
duracion: 4
video: m00-bienvenida
quiz:
  # ─── Pregunta 1: por qué los cálculos esperan turno ────────────────────────

  - clave: m00-compartido
    enunciado: >-
      Apolo lo comparten cientos de investigadores. ¿Qué pasa con tu cálculo
      cuando lo envías?

    opciones:
      # Correcta
      - texto: >-
          Espera su turno en una cola y corre cuando hay computadores libres
          con lo que pediste.
        correcta: true

      # Incorrecta
      - texto: Empieza de inmediato en el computador al que te conectaste.

      # Incorrecta
      - texto: Corre en tu propio computador, pero más rápido.

    explicacion: >-
      En un clúster compartido nadie corre sus cálculos donde quiera: cada uno
      dice qué necesita, el cálculo espera su turno en una cola y, cuando hay
      espacio, corre en los computadores de Apolo. Así todos tienen su parte.
      En los módulos 5 y 6 aprendes a hacerlo.

  # ─── Pregunta 2: qué hace falta para aprobar ───────────────────────────────

  - clave: m00-aprobar
    enunciado: >-
      ¿Qué necesitas para aprobar el curso? Marca todas las que apliquen.

    opciones:
      # Correcta
      - texto: Completar todas las lecciones, incluido el quiz final.
        correcta: true

      # Correcta
      - texto: Aprobar las siete prácticas en la VM de práctica.
        correcta: true

      # Correcta
      - texto: Que un instructor apruebe tu graduación en tu clúster real.
        correcta: true

      # Incorrecta
      - texto: Saber usar Linux antes de empezar.

    explicacion: >-
      Para aprobar se necesitan tres cosas: las lecciones completas, las siete
      prácticas aprobadas y la graduación, un trabajo corto en tu clúster real
      que revisa un instructor. No necesitas saber Linux ni haber usado un
      clúster: el curso empieza desde cero.
---

## Objetivos

Al terminar podrás:

- Explicar qué es Apolo y para qué te sirve.
- Entender por qué en un clúster compartido los cálculos esperan su turno.
- Saber cómo funciona el curso y qué necesitas para aprobarlo.

## Resumen

### 1. Qué es Apolo

**Apolo** es el Centro de Computación Científica de la Universidad EAFIT. Pone
a tu disposición computadores mucho más potentes que el tuyo, para cálculos que
en tu equipo tardarían días o no cabrían en la memoria: simulaciones, análisis
de datos, entrenamiento de modelos.

Esos computadores forman un **clúster**: muchos computadores, llamados
**nodos**, conectados entre sí y compartidos por todos los usuarios.

### 2. Un clúster compartido

Como el clúster es de todos, nadie corre sus cálculos donde quiera. Cada uno
dice qué necesita (cuántos núcleos, cuánta memoria, cuánto tiempo), su cálculo
**espera su turno en una cola** y, cuando hay espacio, corre en los nodos de
Apolo. Mientras tanto puedes apagar tu computador: el cálculo sigue.

No necesitas saber cómo se hace todavía. Lo vas a aprender paso a paso en este
curso.

### 3. Apolo II y Apolo III

Apolo tiene dos clústeres, **Apolo II** y **Apolo III**. Se usan casi igual, y
tu cuenta está en uno de los dos. No tienes que averiguar cuál: la plataforma
ya lo sabe y te muestra lo de tu clúster. Cuando algo cambie entre los dos,
verás pestañas como estas, y se abre la tuya:

::: apolo2

**Tu clúster es Apolo II.**

:::

::: apolo3

**Tu clúster es Apolo III.**

:::

Si la que se abrió no es la de tu clúster, escribe a `apolo@eafit.edu.co`.

### 4. Qué vas a aprender

| Módulo | Qué aprendes                                         |
| ------ | ---------------------------------------------------- |
| 1      | Conectarte a Apolo desde tu computador.              |
| 2      | Moverte en la terminal de Linux.                     |
| 3      | Subir y bajar tus archivos.                          |
| 4      | Cargar el software que ya está instalado en Apolo.   |
| 5      | Enviar tus cálculos a la cola y seguirlos.           |
| 6      | Usar varios núcleos sin desperdiciar recursos.       |
| 7      | Editar desde VS Code y graduarte en tu clúster real. |
| 8      | Instalar tu propio software con conda.               |
| 9      | Cómo pedir ayuda y el quiz final.                    |

No necesitas saber Linux ni haber usado un clúster antes.

### 5. Cómo funciona el curso

1. **Ves el video y respondes el quiz** de cada módulo. El quiz se aprueba con
   80 % y lo puedes repetir las veces que quieras. Al completar un módulo se
   abre el siguiente.
2. **Practicas en la VM de práctica**, una máquina que imita tu clúster. Ahí
   escribes los comandos de verdad, y si te equivocas, solo te afecta a ti.
   Cada práctica se revisa sola y su resultado aparece en Mi progreso.
3. **Te gradúas en tu clúster real**, en el módulo 7, con un trabajo corto que
   revisa un instructor.

Para aprobar necesitas las tres cosas:

- Todas las lecciones completas, incluido el quiz final.
- Las siete prácticas aprobadas.
- La graduación aprobada.

Con eso, el equipo de Apolo le pone a tu cuenta los límites normales de tu
clúster. Todo el curso toma entre 60 y 90 minutos, y puedes dejarlo y seguir
después donde quedaste.

Ahora responde las dos preguntas de abajo y sigue con el módulo 1.
