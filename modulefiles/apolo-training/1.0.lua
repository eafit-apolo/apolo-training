-- apolo-training/1.0.lua
-- Verificador y material del curso de inducción de Apolo.
-- La ruta de instalación se define al desplegar (V-06): <ruta-de-instalacion>
-- debe tener bin/apolo-training y labs/.

help([[
Verificador y material del curso de inducción de Apolo.
Apolo induction course checker and material.

  apolo-training preparar
  apolo-training verificar PRÁCTICA
  apolo-training progreso
  apolo-training ayuda
]])

whatis("Name: apolo-training")
whatis("Version: 1.0")
whatis("Description: verificador y material del curso de inducción de Apolo")

local base = "<ruta-de-instalacion>/apolo-training/1.0"
prepend_path("PATH", pathJoin(base, "bin"))
setenv("APOLO_TRAINING", base)
