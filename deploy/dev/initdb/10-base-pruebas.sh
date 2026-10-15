#!/bin/sh
# Crea la base de las pruebas (servicio `pruebas` de deploy/compose.dev.yaml).
# La imagen de PostgreSQL corre esta carpeta una sola vez, con el volumen vacío.
# Es .sh y no .sql porque el .gitignore del repo ignora *.sql.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -c 'CREATE DATABASE apolo_training_test'
