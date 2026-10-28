/** Pantallas de cuenta: no tiene sentido volver a ellas después de entrar. */
const DE_CUENTA = ['/ingresar', '/cambiar-clave'];

/**
 * El `?volver=` de /ingresar y /cambiar-clave, solo si es una ruta de la app:
 * empieza por una sola `/` y no es una pantalla de cuenta. Cualquier otra cosa
 * (`//otro.sitio`, `https://…`, `/\otro`) se descarta, para que nadie arme un
 * enlace de ingreso que lleve a otro lado.
 */
export function rutaInterna(valor: unknown): string | null {
  if (typeof valor !== 'string' || !valor.startsWith('/')) {
    return null;
  }
  if (valor.startsWith('//') || valor.startsWith('/\\')) {
    return null;
  }
  const ruta = valor.split(/[?#]/)[0];
  if (DE_CUENTA.some((c) => ruta === c || ruta.startsWith(`${c}/`))) {
    return null;
  }
  return valor;
}
