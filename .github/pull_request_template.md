## Tarea

Código del plan (por ejemplo B-03):

## Qué cambia y por qué

## Cómo se probó

Pega aquí la evidencia: salida de comandos, capturas o enlace a la ejecución.

## Definition of Done

Borra los bloques que no apliquen a esta tarea.

### Código

- [ ] La rama es `feat/`, `fix/` o `chore/` y el PR cita el código de la tarea.
- [ ] Revisado y aprobado por el otro; nadie fusiona su propio PR.
- [ ] CI en verde: lint, pruebas y build.
- [ ] Pruebas nuevas para lo nuevo; nada de probar solo a mano.
- [ ] Sin secretos, contraseñas ni datos de usuarios en el repo.
- [ ] README o docs/ actualizados si cambia cómo se usa.
- [ ] Desplegado en la 117 (o la 116) y probado ahí, no solo en local.

### Infraestructura

- [ ] Todo en un rol de Ansible; nada hecho a mano que no quede en el repo.
- [ ] Rol idempotente: la segunda corrida termina con `changed=0`.
- [ ] Comandos sobre dev2 o los clústeres revisados antes por la coordinación.
- [ ] Secretos en Ansible Vault o en secrets de Docker Compose, nunca en el repo.
- [ ] Evidencia (salida de comandos) pegada en la nota de la tarea.
- [ ] Runbook en Affine si deja una operación que se repite.

### Contenido

- [ ] Archivo en `content/es/` con la plantilla y validado por el importador.
- [ ] Cada comando probado en la 116 y en el clúster real que corresponda.
- [ ] Pestañas Apolo II / Apolo III donde algo cambia.
- [ ] Quiz con explicación en cada respuesta.
- [ ] Revisado por el otro; sin datos personales ni de otros usuarios.

### Videos y subtítulos

- [ ] MP4 H.264/AAC 1080p, 5 minutos o menos, audio a −16 LUFS.
- [ ] Nada sensible en pantalla: contraseñas, correos o sesiones ajenas.
- [ ] VTT en español e inglés revisados por una persona.
- [ ] Subido y visible en la plataforma en los dos idiomas.

### Gestión y pruebas

- [ ] Resultado escrito (acta, tabla o informe) en el repo o en Affine.
- [ ] Enlazado en la nota de la tarea.
- [ ] Comunicado a quien lo necesita para seguir.

### Repositorio público

- [ ] Sin IPs, nombres internos ni nombres de usuario en lo que sube este PR.
