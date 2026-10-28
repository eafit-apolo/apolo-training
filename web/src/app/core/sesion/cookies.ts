/**
 * Valor de una cookie que la app puede leer (no `HttpOnly`), o `null` si no
 * está. La API solo deja legible `csrf`; `at` y `rt` nunca llegan aquí.
 */
export function leerCookie(documento: Document, nombre: string): string | null {
  const prefijo = `${nombre}=`;
  for (const parte of documento.cookie.split(';')) {
    const cookie = parte.trim();
    if (cookie.startsWith(prefijo)) {
      const valor = cookie.slice(prefijo.length);
      try {
        return decodeURIComponent(valor);
      } catch {
        return valor;
      }
    }
  }
  return null;
}

/** Cookie que la API pone al iniciar sesión y que la app devuelve en `X-CSRF-Token`. */
export const COOKIE_CSRF = 'csrf';
export const CABECERA_CSRF = 'X-CSRF-Token';
