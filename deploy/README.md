# deploy

`compose.yaml` y `nginx.conf` de la plataforma en la 117. Cada servicio trae su
`Dockerfile` en su propia carpeta (`api/Dockerfile`, `web/Dockerfile`…), y el
dueño de las imágenes va en la variable `IMAGE_PREFIX`.
