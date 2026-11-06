---
id: m01/ssh
titulo: Entrar por SSH
orden: 2
duracion: 8
video: m01-ssh
practicas: [conexion]
quiz:
  # ─── Pregunta 1: para qué es la VPN ────────────────────────────────────────

  - clave: m01-vpn
    enunciado: >-
      ¿Para qué necesitas la VPN de EAFIT en este curso? Marca todas las que
      apliquen.

    opciones:
      # Correcta
      - texto: Para conectarte por SSH al login de tu clúster.
        correcta: true

      # Correcta
      - texto: Para conectarte por SSH a la VM de práctica.
        correcta: true

      # Incorrecta
      - texto: Para que tus trabajos corran más rápido en Slurm.

      # Incorrecta
      - texto: Para cifrar lo que escribes en SSH, que sin VPN viaja a la vista.

    explicacion: >-
      Apolo II, Apolo III y la VM de práctica solo aceptan conexiones desde la
      red de Apolo, y la VPN pone tu computador en esa red. Sin ella, `ssh` se
      queda esperando y termina en `Connection timed out`. SSH ya cifra todo por
      su cuenta, y la VPN no cambia la velocidad de los trabajos: corren en los
      nodos de cómputo, no en tu computador.

  # ─── Pregunta 2: qué contraseña pide cada lugar ────────────────────────────

  - clave: m01-contrasenas
    enunciado: >-
      Ya cambiaste la contraseña temporal en esta plataforma. Ahora entras por
      primera vez por SSH a la VM de práctica. ¿Qué contraseña escribes?

    opciones:
      # Correcta
      - texto: >-
          La temporal que te dieron con tu cuenta del curso. Luego la VM te pide
          una nueva.
        correcta: true

      # Incorrecta
      - texto: La nueva que acabas de poner en la plataforma.

      # Incorrecta
      - texto: La de la VPN.

    explicacion: >-
      La contraseña de la plataforma y la de la VM de práctica empiezan iguales,
      con la temporal, pero son dos contraseñas distintas. Cada una se cambia en
      su primer ingreso y desde ahí no dependen la una de la otra: cambiar la de
      la plataforma no cambia la de la VM. La VPN y tu clúster real tienen sus
      propias credenciales, las que te dio el equipo de Apolo.
---

## Objetivos

Al terminar podrás:

- Conectarte por SSH al login de tu clúster.
- Reconocer la huella del servidor y saber cuándo aceptarla.
- Cambiar la contraseña temporal en tu primer ingreso.

## Resumen

### 1. Abre una terminal

- **Windows 10 u 11:** abre **PowerShell**, que ya trae el comando `ssh`.
- **macOS:** abre **Terminal**.
- **Linux:** abre la terminal de tu escritorio.

Enciende la VPN antes de seguir.

### 2. Conéctate al login de tu clúster

::: apolo2

```bash
ssh <usuario>@apolo.eafit.edu.co
```

:::

::: apolo3

```bash
ssh <usuario>@apolo-3.eafit.edu.co
```

:::

Cambia `<usuario>` por tu usuario del clúster. Cuando escribas la contraseña no
aparece nada en la pantalla, ni siquiera asteriscos: es normal. Escríbela y
pulsa Enter.

### 3. La huella del servidor

La primera vez que te conectas a un servidor, `ssh` te muestra su huella y te
pregunta si confías en él:

```text
The authenticity of host '<servidor> (<IP>)' can't be established.
ED25519 key fingerprint is SHA256:<huella>.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Escribe `yes` y pulsa Enter. Tu computador guarda la huella y no vuelve a
preguntar por ese servidor.

Si algún día `ssh` dice `REMOTE HOST IDENTIFICATION HAS CHANGED`, no sigas:
puede que no estés hablando con el servidor de Apolo. Escribe al equipo de
Apolo.

### 4. Cambia la contraseña temporal

En tu primer ingreso, la contraseña que te dieron ya está vencida. Después de
escribirla, el servidor te pide cambiarla:

```text
WARNING: Your password has expired.
You must change your password now and login again!
Current password:
New password:
Retype new password:
passwd: all authentication tokens updated successfully.
```

1. En `Current password`, escribe otra vez la temporal.
2. En `New password` y `Retype new password`, la nueva, dos veces igual. Usa
   al menos 8 caracteres y mezcla mayúsculas, minúsculas, números y símbolos.
3. La conexión se cierra sola. Vuelve a conectarte con la contraseña nueva.

Cuando el prompt cambia a `[<usuario>@<servidor> ~]$`, todo lo que escribas
corre en el servidor, no en tu computador. Para salir:

```bash
exit
```

### 5. Una contraseña por lugar

| Dónde                       | Qué contraseña                                                     |
| --------------------------- | ------------------------------------------------------------------ |
| VPN                         | La de la VPN, que te dio el equipo de Apolo.                       |
| Tu clúster (Apolo II o III) | La de tu cuenta del clúster, que te dio el equipo de Apolo.        |
| VM de práctica              | La del curso: empieza con la temporal y la cambias en la práctica. |
| Esta plataforma             | La del curso: empieza con la misma temporal y la cambiaste aquí.   |

La de la VM y la de la plataforma empiezan iguales, pero cada una se cambia por
separado y desde ahí son independientes.

## Práctica

En la VM de práctica (`apolo-training.apolo.eafit.edu.co`), con tu usuario del
curso:

1. Con la VPN encendida, conéctate:

   ```bash
   ssh <usuario>@apolo-training.apolo.eafit.edu.co
   ```

2. Acepta la huella con `yes`, escribe la contraseña temporal y cámbiala por
   una nueva. La conexión se cierra sola.
3. Vuelve a conectarte con la contraseña nueva y comprueba dónde estás. Debe
   salir el nombre de la VM de práctica, no el de tu computador:

   ```bash
   hostname
   ```

4. Verifica:

   ```bash
   apolo-training verificar conexion
   ```

La contraseña que acabas de poner es la de la VM. La de la plataforma sigue
siendo la que pusiste aquí.

## Si algo falla

- **`ssh` se queda esperando y termina en `Connection timed out`:** la VPN está
  apagada. Enciéndela y vuelve a intentarlo.
- **`Permission denied, please try again.`:** el usuario o la contraseña no son
  los de ese lugar. Revisa la tabla de arriba y la dirección: tu clúster, o la
  VM de práctica con tu usuario del curso.
- **`BAD PASSWORD: The password is shorter than 8 characters`** o
  **`BAD PASSWORD: The password fails the dictionary check`:** la contraseña
  nueva es muy corta o muy fácil de adivinar. Escribe otra.
- **`Sorry, passwords do not match.`:** las dos veces que escribiste la
  contraseña nueva no coinciden. Vuelve a conectarte y repite el cambio.
- **`apolo-training: command not found`:** carga el verificador con
  `module load apolo-training` y vuelve a correr el comando.
- **`apolo-training verificar conexion` dice que no ve una sesión SSH:** córrelo
  dentro de la conexión por SSH a la VM, no en la terminal de tu computador.

¿Sigue sin funcionar? Escribe a `apolo@eafit.edu.co` con tu usuario, el comando
que corriste y el mensaje de error.
