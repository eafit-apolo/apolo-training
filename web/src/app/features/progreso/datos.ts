import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import type { Idioma } from '../../core/i18n/idioma';
import type { Cluster } from '../../core/sesion/sesion';
import { API } from '../../core/sesion/sesion';
import type { EstadoModuloApi, LeccionRefApi, Practica } from '../cursos/datos/api';

// Esquemas de `GET /api/me/progreso` (B-06 y B-07) y `POST /api/me/graduacion`
// (B-07) de api/openapi.yaml. En la API una práctica se llama `lab`.

/** Las siete prácticas, en el orden del curso (`PRACTICAS` de la API). */
export const PRACTICAS: readonly Practica[] = [
  'conexion',
  'terminal',
  'archivos',
  'modulos',
  'memoria',
  'nucleos',
  'paralelo',
];

/** `SINCRONIZACION_ATRASADA` de la API: la VM reporta cada 5 minutos. */
export const MINUTOS_ATRASO = 15;

/** Patrón del JobID de `GraduacionEntrada` (`1234` o `1234_5`). */
export const PATRON_JOBID = /^[0-9]+(_[0-9]+)?$/;
/** Largo máximo de la salida del verificador (`GraduacionEntrada.salida`). */
export const SALIDA_MAXIMA = 4000;

export interface LeccionProgresoApi {
  readonly id: number;
  readonly slug: string;
  readonly titulo: string;
  readonly completada: boolean;
  readonly video_completo: boolean;
  readonly tiene_quiz: boolean;
  readonly quiz_aprobado: boolean;
  /** 0 a 100; `null` sin quiz o sin intentos. */
  readonly quiz_mejor_puntaje: number | null;
  /** Las prácticas que explica esta lección (F-07). */
  readonly practicas: readonly Practica[];
}

export interface ModuloProgresoApi {
  readonly id: number;
  readonly slug: string;
  readonly numero: number;
  readonly titulo: string;
  readonly estado: EstadoModuloApi;
  readonly lecciones_total: number;
  readonly lecciones_completas: number;
  readonly lecciones: readonly LeccionProgresoApi[];
}

export type EstadoLab = 'sin_intentar' | 'intentado' | 'aprobado';

export interface LabEstadoApi {
  readonly lab: Practica;
  readonly estado: EstadoLab;
  readonly jobid: string | null;
  readonly fecha: string | null;
  readonly detalle: string | null;
}

export type EstadoGraduacion = 'enviada' | 'aprobada' | 'rechazada';

export interface GraduacionApi {
  readonly cluster: Cluster;
  readonly jobid: string;
  readonly salida_verificador: string;
  readonly estado: EstadoGraduacion;
  readonly enviada_en: string;
  readonly revisada_en: string | null;
  readonly comentario: string | null;
  readonly qos_aplicada_en: string | null;
}

export type TipoPaso =
  'leccion' | 'laboratorio' | 'graduacion' | 'esperar_revision' | 'esperar_qos' | 'terminado';

export interface SiguientePasoApi {
  readonly tipo: TipoPaso;
  /** Solo con `tipo: leccion`. */
  readonly leccion: LeccionRefApi | null;
  /** Solo con `tipo: laboratorio`. */
  readonly lab: Practica | null;
}

export interface MiProgresoApi {
  /** Slug del curso; `null` si todavía no hay uno publicado. */
  readonly curso: string | null;
  readonly avance_pct: number;
  readonly lecciones_total: number;
  readonly lecciones_completas: number;
  readonly modulos: readonly ModuloProgresoApi[];
  readonly fallback: boolean;
  /** Siempre las siete, en el orden de `PRACTICAS`. */
  readonly labs: readonly LabEstadoApi[];
  /** El último reporte de la VM (el mismo para todos); `null` si nunca llegó. */
  readonly ultima_sincronizacion: string | null;
  /** Más de 15 min sin reporte; `false` si nunca llegó uno. */
  readonly sincronizacion_atrasada: boolean;
  readonly graduacion: GraduacionApi | null;
  readonly aprobado: boolean;
  readonly siguiente_paso: SiguientePasoApi;
}

export interface GraduacionEntradaApi {
  readonly jobid: string;
  readonly salida: string;
}

/** `GET /api/me/progreso` y `POST /api/me/graduacion`. */
@Injectable({ providedIn: 'root' })
export class ProgresoApi {
  private readonly http = inject(HttpClient);

  progreso(idioma: Idioma): Promise<MiProgresoApi> {
    return firstValueFrom(
      this.http.get<MiProgresoApi>(`${API}/me/progreso`, { params: { lang: idioma } }),
    );
  }

  /**
   * Envía (o reenvía) la graduación; el interceptor pone el CSRF. 409
   * `graduacion_aprobada` si ya está aprobada; 422 si el JobID o la salida no
   * cumplen el contrato.
   */
  enviarGraduacion(entrada: GraduacionEntradaApi): Promise<GraduacionApi> {
    return firstValueFrom(this.http.post<GraduacionApi>(`${API}/me/graduacion`, entrada));
  }
}

// --- Lo que la pantalla calcula -------------------------------------------------

/** Dónde se explica una práctica: la primera lección que la nombra. */
export interface LeccionDePractica {
  readonly modulo: string;
  readonly moduloNumero: number;
  readonly slug: string;
  readonly titulo: string;
  /** «5.1»: número del módulo y posición de la lección en él. */
  readonly numero: string;
  /** Un estudiante no puede abrir una lección de un módulo bloqueado. */
  readonly bloqueada: boolean;
}

/** Cada práctica con la lección que la explica (si alguna la nombra). */
export function leccionesDePracticas(
  modulos: readonly ModuloProgresoApi[],
): ReadonlyMap<Practica, LeccionDePractica> {
  const mapa = new Map<Practica, LeccionDePractica>();
  for (const modulo of modulos) {
    modulo.lecciones.forEach((leccion, i) => {
      for (const practica of leccion.practicas) {
        if (!mapa.has(practica)) {
          mapa.set(practica, {
            modulo: modulo.slug,
            moduloNumero: modulo.numero,
            slug: leccion.slug,
            titulo: leccion.titulo,
            numero: `${modulo.numero}.${i + 1}`,
            bloqueada: modulo.estado === 'bloqueado',
          });
        }
      }
    });
  }
  return mapa;
}

/** «5.1» de una lección por su módulo y su slug; `null` si no está. */
export function numeroDeLeccion(
  modulos: readonly ModuloProgresoApi[],
  modulo: string,
  slug: string,
): string | null {
  const encontrado = modulos.find((m) => m.slug === modulo);
  const i = encontrado?.lecciones.findIndex((l) => l.slug === slug) ?? -1;
  return encontrado && i >= 0 ? `${encontrado.numero}.${i + 1}` : null;
}

/** Las cifras de arriba de la pantalla. */
export interface Cifras {
  readonly avance: number;
  readonly modulosCompletos: number;
  readonly modulos: number;
  readonly practicasAprobadas: number;
  readonly practicas: number;
  readonly graduacion: EstadoGraduacion | 'sin_enviar';
}

export function cifrasDe(datos: MiProgresoApi): Cifras {
  return {
    avance: datos.avance_pct,
    modulosCompletos: datos.modulos.filter((m) => m.estado === 'completo').length,
    modulos: datos.modulos.length,
    practicasAprobadas: datos.labs.filter((l) => l.estado === 'aprobado').length,
    practicas: datos.labs.length,
    graduacion: datos.graduacion?.estado ?? 'sin_enviar',
  };
}

/**
 * Si la última sincronización tiene más de 15 minutos. Manda la API (al
 * cargar), pero la página puede quedarse abierta: con el reloj del navegador
 * también se avisa cuando el reporte envejece sin recargar. Sin ningún
 * reporte no hay atraso (la V-05 todavía no ha empezado a mandar).
 */
export function sincronizacionAtrasada(
  ultima: string | null,
  segunLaApi: boolean,
  ahora: number,
): boolean {
  if (ultima === null) {
    return false;
  }
  return segunLaApi || ahora - Date.parse(ultima) > MINUTOS_ATRASO * 60_000;
}

/** Hace cuánto, para `Intl.RelativeTimeFormat`: en minutos, horas o días. */
export function haceCuanto(
  fecha: string,
  ahora: number,
): { readonly valor: number; readonly unidad: 'minute' | 'hour' | 'day' } {
  // Un reloj un poco adelantado en el servidor no da «dentro de 1 min».
  const minutos = Math.max(0, Math.floor((ahora - Date.parse(fecha)) / 60_000));
  if (minutos < 60) {
    return { valor: -minutos, unidad: 'minute' };
  }
  if (minutos < 24 * 60) {
    return { valor: -Math.floor(minutos / 60), unidad: 'hour' };
  }
  return { valor: -Math.floor(minutos / (24 * 60)), unidad: 'day' };
}

/** Qué le falta al formulario de la graduación antes de llamar a la API. */
export type FaltaGraduacion = 'jobid' | 'jobidInvalido' | 'salida' | 'salidaLarga';

export function faltasDeGraduacion(jobid: string, salida: string): readonly FaltaGraduacion[] {
  const faltas: FaltaGraduacion[] = [];
  const id = jobid.trim();
  if (id === '') {
    faltas.push('jobid');
  } else if (!PATRON_JOBID.test(id)) {
    faltas.push('jobidInvalido');
  }
  if (salida.trim() === '') {
    faltas.push('salida');
  } else if ([...salida].length > SALIDA_MAXIMA) {
    // Python cuenta caracteres, no unidades UTF-16.
    faltas.push('salidaLarga');
  }
  return faltas;
}
