---
id: m00/bienvenida
titulo: Bienvenida
orden: 1
duracion: 3
video: m00-bienvenida
quiz:
  - clave: m00-login
    enunciado: >-
      Estás conectado al login de tu clúster. ¿Cuáles de estas cosas sí haces
      ahí?
    opciones:
      - texto: Editar el script de un trabajo y enviarlo a Slurm.
        correcta: true
      - texto: Copiar tus datos a tu carpeta personal.
        correcta: true
      - texto: Correr tu simulación un momento, para ver si funciona.
      - texto: Entrenar un modelo de noche, cuando hay poca gente conectada.
    explicacion: >-
      El login es la entrada que comparten todos los usuarios del clúster: ahí
      editas archivos, mueves datos y envías trabajos. El cómputo, aunque sea
      una prueba corta o de noche, va como trabajo de Slurm, que lo corre en
      un nodo de cómputo con los recursos que pediste. Un programa pesado en el
      login lo vuelve lento para todos.
  - clave: m00-aprobar
    enunciado: ¿Qué necesitas para aprobar el curso?
    opciones:
      - texto: >-
          Completar todas las lecciones, aprobar las prácticas en la VM y que
          un instructor apruebe tu graduación en tu clúster real.
        correcta: true
      - texto: Ver todos los videos y aprobar el quiz de cada módulo.
      - texto: Sacar 80 % o más en el quiz final, sin importar lo demás.
    explicacion: >-
      Los videos y los quices completan las lecciones, incluido el quiz final,
      pero no bastan. También cuentan las siete prácticas de la VM de práctica,
      cada una aprobada con `apolo-training verificar`, y la graduación: un
      trabajo corto en tu clúster real que revisa un instructor.
---

## Objetivos

Al terminar podrás:

- Decir qué es Apolo y en cuál de sus clústeres está tu cuenta.
- Distinguir lo que se hace en el login de lo que va como trabajo de Slurm.
- Saber cómo funciona el curso y qué necesitas para aprobarlo.

## Resumen

**Apolo** es el Centro de Computación Científica de la Universidad EAFIT. Tiene
dos clústeres, Apolo II y Apolo III: grupos de computadores (nodos) que
comparten todos sus usuarios. Tu cuenta está en uno de los dos, y la pestaña de
abajo se abre en el tuyo.

::: apolo2

Tu cuenta está en **Apolo II**. Su login es `apolo.eafit.edu.co`.

La VM de práctica imita Apolo II: ahí ves sus particiones y su software.

:::

::: apolo3

Tu cuenta está en **Apolo III**. Su login es `apolo-3.eafit.edu.co`.

La VM de práctica imita Apolo III: ahí ves sus particiones y su software.

:::

Lo que cambia entre los dos clústeres (cuotas, particiones, software) va en
pestañas como esta a lo largo del curso. Si la pestaña que se abrió no es la de
tu clúster, escribe a `apolo@eafit.edu.co` antes de seguir.

**El login no es para cómputo.** Al conectarte llegas al **nodo de login**, el
mismo para todos los usuarios del clúster. El cómputo va como **trabajo** de
Slurm: Slurm lo pone en la cola y lo corre en un **nodo de cómputo** con los
núcleos, la memoria y el tiempo que pediste. Esos nodos también se comparten,
así que pide lo que vas a usar.

| En el login                      | Como trabajo de Slurm                             |
| -------------------------------- | ------------------------------------------------- |
| Editar archivos y scripts        | Simulaciones, análisis y entrenamientos           |
| Copiar y organizar tus datos     | Programas que usan varios núcleos o mucha memoria |
| Cargar módulos y enviar trabajos | Las pruebas de tu programa, aunque sean cortas    |

**Cómo funciona el curso:**

- **Nueve módulos, del 0 al 8, en orden.** Casi todos traen un video corto, un
  resumen como este, una práctica y un quiz de 1 o 2 preguntas. Cada quiz se
  aprueba con 80 % y lo puedes intentar las veces que quieras. El módulo
  siguiente se abre cuando completas el anterior. Todo toma entre 60 y 90
  minutos.
- **Practicas en la VM de práctica** (`apolo-training.apolo.eafit.edu.co`), una
  máquina con Slurm que imita tu clúster. Te conectas con tu propio cliente SSH
  y la VPN de EAFIT, que configuras en el módulo 1. Ahí un error solo te afecta
  a ti.
- **Cada práctica termina con `apolo-training verificar`** y el nombre de la
  práctica. El resultado aparece en Mi progreso en unos minutos.
- **La graduación es en tu clúster real**, en el módulo 7: tu primer trabajo
  ahí, corto, que revisa un instructor.
- **Apruebas el curso** con todas las lecciones completas, las siete prácticas
  aprobadas y la graduación aprobada. Entonces el equipo de Apolo le pone a tu
  cuenta los límites normales de tu clúster.
