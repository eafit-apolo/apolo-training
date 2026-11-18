# Guion: SSH

| Dato              | Valor                                                               |
| ----------------- | ------------------------------------------------------------------- |
| Lección           | [`m01/ssh`](../es/m01/ssh.md)                                       |
| Archivo del video | `m01-ssh-es.mp4`                                                    |
| Graba             | Byron                                                               |
| Escena de OBS     | `Terminal`; `Pantalla completa` solo para abrir la terminal         |
| Duración estimada | **3 min 20 s** (≈ 360 palabras a 130 por minuto + 35 s de comandos) |

Abrir una terminal, conectarse por SSH, aceptar la huella del servidor, cambiar
la contraseña temporal y saber qué contraseña pide cada lugar. Los comandos y
el orden son los del resumen de la lección.

## Antes de grabar

- Una **cuenta de demostración nueva en la VM de práctica**, con la contraseña
  temporal vencida, como la recibe un usuario del curso. El video se graba
  contra la VM: es la misma conexión que el usuario hace en la práctica, y así
  no sale nada de los clústeres reales.
- Borrar la huella de la VM en el computador que graba, para que `ssh` vuelva a
  preguntarla: `ssh-keygen -R apolo-training.apolo.eafit.edu.co`.
- La VPN encendida antes de empezar.
- Capturas de PowerShell en Windows y de Terminal en macOS, para la parte de
  abrir la terminal (se ponen en Canva).
- Una lámina en Canva con la tabla «Qué contraseña pide cada lugar» del
  resumen.
- **En la edición:** tapar la IP que sale en la pregunta de la huella y cortar
  los momentos en que se escribe una contraseña (OBS en pausa).

## Guion

### 0:00 · Entrada

| Qué se dice                                                                                                                             | Qué se muestra                          |
| --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| «Hola. En este video vas a conectarte por SSH al login de tu clúster, aceptar la huella del servidor y cambiar la contraseña temporal.» | La terminal vacía, con el prompt corto. |

### 0:10 · Abrir una terminal

| Qué se dice                                                                                                                                      | Qué se muestra                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| «Con SSH entras a Apolo desde tu computador: lo que escribes corre en el servidor, no en tu equipo.»                                             | La terminal vacía.                                                                      |
| «Para usarlo, abre una terminal. En Windows, abre PowerShell, que ya trae ssh. En macOS, abre Terminal. En Linux, la terminal de tu escritorio.» | Las tres capturas, una tras otra: PowerShell, Terminal de macOS y la terminal de Linux. |
| «Antes de seguir, revisa que la VPN esté encendida. Sin ella, Apolo no te contesta.»                                                             | El ícono de la VPN conectada en la barra del sistema.                                   |

### 0:35 · El comando

| Qué se dice                                                                                                                                                                                                                      | Qué se muestra                                                                                                                   |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| «El comando es ssh, tu usuario, arroba y la dirección del servidor. Si tu cuenta está en Apolo II, la dirección es apolo punto eafit punto edu punto co. Si está en Apolo III, apolo guion tres punto eafit punto edu punto co.» | Texto sobre la terminal (Canva) con los dos comandos: `ssh <usuario>@apolo.eafit.edu.co` y `ssh <usuario>@apolo-3.eafit.edu.co`. |
| «Yo me conecto a la VM de práctica, que funciona igual. Es la conexión que vas a hacer en la práctica.»                                                                                                                          | Se escribe despacio `ssh <usuario-demo>@apolo-training.apolo.eafit.edu.co` y Enter.                                              |

### 1:00 · La huella del servidor

| Qué se dice                                                                                                                                                | Qué se muestra                                                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| «La primera vez que te conectas a un servidor, ssh te muestra su huella y te pregunta si confías en él. Escribe yes y pulsa Enter; no vuelve a preguntar.» | La pregunta `Are you sure you want to continue connecting (yes/no/[fingerprint])?`; se escribe `yes`. |
| «Si algún día ssh avisa que la huella cambió, no sigas y escríbenos.»                                                                                      | Texto sobre la terminal (Canva) con `REMOTE HOST IDENTIFICATION HAS CHANGED`.                         |

### 1:20 · Cambiar la contraseña temporal

| Qué se dice                                                                                                                              | Qué se muestra                                                                                                                               |
| ---------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| «Ahora pide la contraseña. Mientras la escribes no aparece nada, ni siquiera asteriscos. Es normal: escríbela y pulsa Enter.»            | El prompt `password:`. OBS en pausa mientras se escribe la temporal.                                                                         |
| «En tu primer ingreso, la contraseña temporal ya está vencida, así que el servidor te pide cambiarla.»                                   | `WARNING: Your password has expired.` y `Current password:`.                                                                                 |
| «Primero, otra vez la temporal. Después, la nueva, dos veces: al menos ocho caracteres, con mayúsculas, minúsculas, números y símbolos.» | `Current password:`, `New password:` y `Retype new password:`. OBS en pausa en cada contraseña.                                              |
| «Al terminar, la conexión se cierra sola. Vuelve a conectarte, ahora con la contraseña nueva.»                                           | `passwd: all authentication tokens updated successfully.` y `Connection ... closed.`; flecha arriba, Enter y la contraseña nueva (en pausa). |

### 2:15 · Ya estás adentro

| Qué se dice                                                                  | Qué se muestra                                                         |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| «Ya estás en el servidor: el prompt lo muestra. Con hostname lo compruebas.» | El prompt `[<usuario-demo>@apolo-training ~]$`; se escribe `hostname`. |
| «Para salir, exit.»                                                          | Se escribe `exit`; vuelve el prompt del computador.                    |

### 2:30 · Qué contraseña pide cada lugar

| Qué se dice                                                                                                                                              | Qué se muestra                                                                  |
| -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| «Tienes dos cuentas. La de Apolo, que usas en la VPN y en tu clúster: cuando cambias la temporal en el clúster, esa es también tu contraseña de la VPN.» | Lámina «Qué contraseña pide cada lugar», fila de la VPN y el clúster resaltada. |
| «Y la del curso, que usas en esta plataforma y en la VM de práctica. Las dos empiezan con la misma temporal, pero cada una se cambia por separado.»      | La misma lámina, filas de la VM y la plataforma resaltadas.                     |

### 3:05 · Salida

| Qué se dice                                                                                                                                                | Qué se muestra                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| «Ahora es tu turno: conéctate a la VM de práctica con tu usuario del curso, cambia tu contraseña y, al terminar, corre apolo-training verificar conexion.» | La sección «Práctica» de la lección en la plataforma. |

## Revisión

- [ ] Revisado por Juan antes de grabar.
- [ ] Dura 5 minutos o menos ya editado.
