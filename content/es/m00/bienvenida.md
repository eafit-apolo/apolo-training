---
id: m00/bienvenida
titulo: Bienvenida
orden: 1
duracion: 3
video: m00-bienvenida
quiz:
  # ─── Pregunta 1: qué se hace en el login ───────────────────────────────────

  - clave: m00-login
    enunciado: >-
      Estás conectado al login de tu clúster. ¿Cuáles de estas cosas sí haces
      ahí? Marca todas las que apliquen.

    opciones:
      # Correcta
      - texto: Editar el script de un trabajo y enviarlo a Slurm.
        correcta: true

      # Correcta
      - texto: Copiar tus datos a tu carpeta personal.
        correcta: true

      # Incorrecta
      - texto: Correr tu simulación un momento, para ver si funciona.

      # Incorrecta
      - texto: Entrenar un modelo de noche, cuando hay poca gente conectada.

    explicacion: >-
      El login es la entrada que comparten todos los usuarios del clúster: ahí
      editas archivos, mueves datos y envías trabajos. Todo lo que calcula, así
      sea una prueba corta o de noche, se envía a Slurm, que lo corre en un nodo
      de cómputo. Un programa pesado en el login lo vuelve lento para todos.

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
      - texto: Instalar en tu computador el software que vas a usar en Apolo.

    explicacion: >-
      Para aprobar se necesitan tres cosas: las lecciones completas, las siete
      prácticas aprobadas con `apolo-training verificar` y la graduación, un
      trabajo corto en tu clúster real que revisa un instructor. No hace falta
      instalar nada en tu computador: el software ya está en Apolo y se carga
      con módulos.
---

## Objetivos

Al terminar podrás:

- Explicar qué es Apolo.
- Saber si tu cuenta está en Apolo II o en Apolo III.
- Distinguir qué se hace en el login y qué se envía a Slurm.
- Saber qué necesitas para aprobar el curso.

## Resumen

### 1. Qué es Apolo

**Apolo** es el Centro de Computación Científica de la Universidad EAFIT. Pone
a tu disposición computadores mucho más potentes que el tuyo, para cálculos que
en tu equipo tardarían días o no cabrían en la memoria.

Esos computadores forman un **clúster**: muchos computadores, llamados
**nodos**, conectados entre sí y compartidos por todos los usuarios.

### 2. Apolo II y Apolo III

Apolo tiene dos clústeres. Se usan igual: te conectas por SSH, cargas el
software con módulos y envías tus trabajos a Slurm. Lo que cambia son algunos
detalles:

|                                | Apolo II                         | Apolo III                |
| ------------------------------ | -------------------------------- | ------------------------ |
| Dirección para conectarte      | `apolo.eafit.edu.co`             | `apolo-3.eafit.edu.co`   |
| Espacio en tu carpeta personal | Hasta 200 GB, para todo tu grupo | Hasta 200 GB, solo tuyos |
| Interfaz web (OnDemand)        | No tiene                         | Sí, fuera de este curso  |

Tu cuenta está en uno solo de los dos. La pestaña de abajo se abre en el tuyo:

::: apolo2

**Tu clúster es Apolo II.** Te conectas a `apolo.eafit.edu.co`.

:::

::: apolo3

**Tu clúster es Apolo III.** Te conectas a `apolo-3.eafit.edu.co`.

:::

Cada vez que algo cambie entre los dos clústeres, verás pestañas como estas. Si
la que se abrió no es la de tu clúster, escribe a `apolo@eafit.edu.co`.

### 3. El login no es para cómputo

Cuando te conectas a Apolo llegas al **nodo de login**. Piensa en él como la
recepción de un edificio: todos entran por ahí, pero nadie se queda a trabajar
en ella. Si corres algo pesado en el login, se vuelve lento para todos.

Así se trabaja en Apolo:

1. Te conectas al **login** desde tu computador.
2. Preparas tus archivos y un script que dice qué correr y cuántos recursos
   necesita.
3. **Envías ese script a Slurm**, que lo pone en la cola.
4. Cuando hay espacio, Slurm lo corre en un **nodo de cómputo**.
5. Revisas los resultados desde el login.

| En el login, sí                   | En el login, no: se envía a Slurm               |
| --------------------------------- | ----------------------------------------------- |
| Editar archivos y scripts         | Correr simulaciones o análisis                  |
| Copiar y organizar tus datos      | Entrenar modelos                                |
| Cargar módulos                    | Probar tu programa «solo un momento»            |
| Enviar trabajos y revisar la cola | Cualquier cosa que use muchos núcleos o memoria |

### 4. Cómo funciona el curso

1. **Ves el video y respondes el quiz** de cada módulo, del 0 al 8. El quiz se
   aprueba con 80 % y lo puedes repetir las veces que quieras. Al completar un
   módulo se abre el siguiente.
2. **Practicas en la VM de práctica** (`apolo-training.apolo.eafit.edu.co`), una
   máquina que imita tu clúster. Ahí escribes los comandos de verdad, y un error
   solo te afecta a ti. Cada práctica termina con `apolo-training verificar` y
   su resultado aparece en Mi progreso.
3. **Te gradúas en tu clúster real**, en el módulo 7, con un trabajo corto que
   revisa un instructor.

Para aprobar necesitas las tres cosas:

- Todas las lecciones completas, incluido el quiz final.
- Las siete prácticas aprobadas.
- La graduación aprobada.

Con eso, el equipo de Apolo le pone a tu cuenta los límites normales de tu
clúster. Todo el curso toma entre 60 y 90 minutos, y puedes dejarlo y seguir
después donde quedaste.

Ahora responde las dos preguntas de abajo y sigue con el módulo 1, donde te
conectas a Apolo por primera vez.
