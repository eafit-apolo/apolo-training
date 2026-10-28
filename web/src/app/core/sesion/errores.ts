import { HttpErrorResponse } from '@angular/common/http';

/**
 * El `codigo` del cuerpo `{"detail", "codigo"}` de un error de la API, o
 * `null` si no lo trae (sin conexión, un proxy que respondió HTML…).
 */
export function codigoDeError(error: unknown): string | null {
  if (!(error instanceof HttpErrorResponse)) {
    return null;
  }
  const cuerpo: unknown = error.error;
  if (
    typeof cuerpo === 'object' &&
    cuerpo !== null &&
    'codigo' in cuerpo &&
    typeof cuerpo.codigo === 'string'
  ) {
    return cuerpo.codigo;
  }
  return null;
}

/** Un campo extra del cuerpo del error, como `bloqueado_hasta`. */
export function campoDeError(error: unknown, campo: string): unknown {
  if (!(error instanceof HttpErrorResponse)) {
    return undefined;
  }
  const cuerpo: unknown = error.error;
  return typeof cuerpo === 'object' && cuerpo !== null
    ? (cuerpo as Record<string, unknown>)[campo]
    : undefined;
}

/** `status` de la respuesta: 0 si no hubo respuesta (sin red, VPN caída). */
export function estadoDeError(error: unknown): number | null {
  return error instanceof HttpErrorResponse ? error.status : null;
}
