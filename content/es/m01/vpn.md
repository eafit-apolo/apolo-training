---
id: m01/vpn
titulo: La VPN de EAFIT
orden: 1
duracion: 3
video:
  windows: m01-vpn-windows
  macos: m01-vpn-macos
  linux: m01-vpn-linux
---

## Objetivos

Al terminar podrás:

- Instalar el cliente de la VPN de EAFIT en tu sistema operativo.
- Conectarte a la VPN y saber cuándo está encendida.
- Saber qué deja de funcionar si la VPN está apagada.

## Resumen

Apolo II, Apolo III y la VM de práctica solo aceptan conexiones desde la red de
Apolo. La VPN pone tu computador en esa red, estés donde estés.

Entras con tu usuario y contraseña de Apolo, los mismos de tu clúster. La
primera vez usas la contraseña temporal que te dio el equipo de Apolo. Cuando la
cambies en tu primer ingreso al clúster (lección siguiente), la VPN también te
pedirá la nueva.

Arriba está el video de tu sistema operativo. Estos son sus pasos:

### Windows

1. En el navegador, abre <https://leto.omega.eafit.edu.co> e inicia sesión con
   tu usuario y contraseña de Apolo.
2. Descarga GlobalProtect para Windows e instálalo con las opciones que trae.
3. Abre GlobalProtect desde el ícono que aparece junto al reloj, en la barra de
   tareas. En **Portal** escribe `leto.omega.eafit.edu.co` y conéctate.
4. Escribe tu usuario y contraseña. Cuando diga **Conectado**, la VPN está
   encendida.

### macOS

1. En el navegador, abre <https://leto.omega.eafit.edu.co> e inicia sesión con
   tu usuario y contraseña de Apolo.
2. Descarga GlobalProtect para macOS e instálalo.
3. Si macOS avisa que bloqueó software del desarrollador, abre **Configuración
   del Sistema → Privacidad y seguridad** y pulsa **Permitir**.
4. Abre GlobalProtect desde el ícono de la barra de menús, arriba a la derecha.
   En **Portal** escribe `leto.omega.eafit.edu.co` y conéctate.
5. Escribe tu usuario y contraseña. Cuando diga **Conectado**, la VPN está
   encendida.

### Linux

En Linux te conectas con `openconnect`, un cliente libre que habla el mismo
protocolo que GlobalProtect.

1. Instala `openconnect` con el gestor de paquetes de tu distribución:

   ```bash
   sudo apt install openconnect       # Ubuntu y Debian
   sudo dnf install openconnect       # Fedora, Rocky y RHEL
   sudo pacman -S openconnect         # Arch
   ```

2. Conéctate al portal de la VPN:

   ```bash
   sudo openconnect --protocol=gp leto.omega.eafit.edu.co --background
   ```

   Primero te pide la contraseña de tu computador (por `sudo`) y luego tu
   usuario y contraseña de Apolo.

3. Cuando te devuelve el prompt, la VPN está encendida. Con `--background`
   sigue corriendo aunque cierres la terminal.

Para apagar la VPN:

```bash
sudo pkill openconnect
```

### Déjala encendida

Mantén la VPN encendida todo el tiempo que trabajes en Apolo: mientras estés
conectado por SSH y mientras subas o descargues archivos. Si se apaga, la
conexión se corta.

La guía completa, con capturas de cada paso, está en apolo-docs:
[_Configure the VPN_](https://apolo-docs.readthedocs.io/en/latest/gettingstarted/configure_vpn.html).

## Si algo falla

- **En macOS, GlobalProtect se queda girando y no conecta:** abre
  **Configuración del Sistema → Privacidad y seguridad** y pulsa **Permitir**
  junto al aviso de GlobalProtect. Si no aparece el aviso, cierra GlobalProtect
  por completo y ábrelo otra vez.
- **Después de suspender el computador, la VPN no vuelve a conectar:** cierra
  el cliente y ábrelo de nuevo.
- **La VPN rechaza tu usuario o contraseña:** usa tu usuario y contraseña de
  Apolo, los mismos de tu clúster, no los de esta plataforma. Si ya cambiaste
  la contraseña temporal en el clúster, la VPN te pide la nueva.
- **En Linux, `openconnect: command not found`:** no quedó instalado. Repite el
  paso 1 con el comando de tu distribución.
- **En Linux, la VPN no responde después de suspender el computador:** apágala
  con `sudo pkill openconnect` y vuelve a correr el comando del paso 2.

¿Sigue sin funcionar? Escribe a `apolo@eafit.edu.co` con tu usuario, tu sistema
operativo y el mensaje de error.
