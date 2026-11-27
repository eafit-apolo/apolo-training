import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import type { Idioma } from '../../core/i18n/idioma';
import type { Cluster } from '../../core/sesion/sesion';
import { API } from '../../core/sesion/sesion';
import type { LeccionRefApi } from '../cursos/datos/api';
import type { EstadoGraduacion, GraduacionApi } from '../progreso/datos';

// Esquemas del grupo `panel` de api/openapi.yaml (instructor y admin):
// `ResumenPanel` (F-08), `GraduacionAdmin` (B-07) y `VideoAdmin` (B-05).

export interface AvanceModuloApi {
  readonly numero: number;
  readonly titulo: string;
  /** Estudiantes activos que completaron el módulo. */
  readonly completos: number;
}

export interface ResumenPanelApi {
  readonly estudiantes_activos: number;
  readonly sin_empezar: number;
  readonly en_curso: number;
  readonly aprobados: number;
  readonly graduaciones_por_revisar: number;
  readonly aprobados_pendientes_qos: number;
  readonly ultima_sincronizacion: string | null;
  readonly avance_por_modulo: readonly AvanceModuloApi[];
}

export interface GraduacionAdminApi extends GraduacionApi {
  readonly username: string;
  readonly nombre: string;
  readonly revisada_por: string | null;
  /** De las siete prácticas de la VM. */
  readonly labs_aprobados: number;
}

export type Decision = 'aprobar' | 'rechazar';

export interface VideoAdminApi {
  readonly id: number;
  readonly clave: string;
  /** `false` mientras no se haya subido el MP4. */
  readonly disponible: boolean;
  readonly duracion_seg: number | null;
  readonly tamano_bytes: number | null;
  readonly subtitulos: { readonly es: boolean; readonly en: boolean };
  readonly lecciones: readonly LeccionRefApi[];
  readonly subido_por: string | null;
  readonly subido_en: string | null;
}

/** El grupo `panel` de la API, menos las subidas (van por `SubidasApi`). */
@Injectable({ providedIn: 'root' })
export class PanelApi {
  private readonly http = inject(HttpClient);

  /** `?lang=`: la web cambia el idioma antes de que termine el `PATCH /me`. */
  resumen(idioma: Idioma): Promise<ResumenPanelApi> {
    return firstValueFrom(
      this.http.get<ResumenPanelApi>(`${API}/panel/resumen`, { params: { lang: idioma } }),
    );
  }

  /** Las más viejas primero; sin `estado`, todas. */
  graduaciones(estado: EstadoGraduacion | null): Promise<GraduacionAdminApi[]> {
    return firstValueFrom(
      this.http.get<GraduacionAdminApi[]>(`${API}/panel/graduaciones`, {
        params: estado ? { estado } : {},
      }),
    );
  }

  /**
   * 422 `comentario_obligatorio` si se rechaza sin comentario; 409
   * `sin_graduacion_pendiente` si ya no está `enviada` (otra persona la revisó).
   */
  revisar(username: string, decision: Decision, comentario: string): Promise<GraduacionAdminApi> {
    const texto = comentario.trim();
    return firstValueFrom(
      this.http.post<GraduacionAdminApi>(
        `${API}/panel/graduaciones/${encodeURIComponent(username)}/revision`,
        { decision, comentario: texto === '' ? null : texto },
      ),
    );
  }

  videos(idioma: Idioma): Promise<VideoAdminApi[]> {
    return firstValueFrom(
      this.http.get<VideoAdminApi[]>(`${API}/panel/videos`, { params: { lang: idioma } }),
    );
  }
}

// --- Lo que las pantallas calculan ---------------------------------------------

/** `GET /panel/export/progreso.csv`, de todos o de un clúster. */
export function urlCsv(cluster: Cluster | null): string {
  const base = `${API}/panel/export/progreso.csv`;
  return cluster ? `${base}?cluster=${cluster}` : base;
}

/**
 * Para confirmar la graduación en el clúster real: el trabajo de ese usuario
 * con su nombre, partición y estado (`-D` por si el JobID se repite, V-09).
 */
export function comandoConfirmar(
  graduacion: Pick<GraduacionAdminApi, 'jobid' | 'username'>,
): string {
  return `sacct -D -j ${graduacion.jobid} -u ${graduacion.username} -o JobID,JobName,Partition,State,Elapsed`;
}

/** El módulo donde más estudiantes se quedan, con cuántos venían y cuántos pasan. */
export interface Salto {
  readonly numero: number;
  readonly titulo: string;
  readonly antes: number;
  readonly despues: number;
}

/**
 * «Dónde se atascan»: el módulo con la mayor caída respecto del anterior (al
 * primero llegan todos los activos). Si nadie se queda en ninguno, `null`.
 * Con un empate, el primero.
 */
export function mayorSalto(modulos: readonly AvanceModuloApi[], activos: number): Salto | null {
  let mejor: Salto | null = null;
  let antes = activos;
  for (const m of modulos) {
    const caida = antes - m.completos;
    if (caida > 0 && (!mejor || caida > mejor.antes - mejor.despues)) {
      mejor = { numero: m.numero, titulo: m.titulo, antes, despues: m.completos };
    }
    antes = m.completos;
  }
  return mejor;
}

/** «4:05»: minutos y segundos (o «1:02:30» si pasa de la hora). */
export function duracion(segundos: number): string {
  const s = Math.max(0, Math.round(segundos));
  const horas = Math.floor(s / 3600);
  const minutos = Math.floor((s % 3600) / 60);
  const resto = String(s % 60).padStart(2, '0');
  return horas > 0
    ? `${horas}:${String(minutos).padStart(2, '0')}:${resto}`
    : `${minutos}:${resto}`;
}

// --- Subidas -----------------------------------------------------------------------

/** Qué se sube: el MP4 o los subtítulos de un idioma. */
export type Destino = 'video' | Idioma;

/** Lo mismo que la API (`LIMITE_VIDEO`, `LIMITE_VTT`) y `client_max_body_size 2G`. */
export const LIMITE_VIDEO = 2 * 1024 ** 3;
export const LIMITE_VTT = 1024 ** 2;

export type FaltaArchivo = 'vacio' | 'noMp4' | 'noVtt' | 'muyGrande';

/**
 * Lo que se puede saber del archivo antes de subirlo: la extensión (o el tipo
 * que da el navegador) y el tamaño. El formato de verdad (H.264 + AAC, WebVTT
 * en UTF-8) lo revisa la API al recibirlo.
 */
export function revisarArchivo(destino: Destino, archivo: File): FaltaArchivo | null {
  const nombre = archivo.name.toLowerCase();
  if (destino === 'video') {
    if (!nombre.endsWith('.mp4') && archivo.type !== 'video/mp4') {
      return 'noMp4';
    }
  } else if (!nombre.endsWith('.vtt') && archivo.type !== 'text/vtt') {
    return 'noVtt';
  }
  if (archivo.size === 0) {
    return 'vacio';
  }
  return archivo.size > (destino === 'video' ? LIMITE_VIDEO : LIMITE_VTT) ? 'muyGrande' : null;
}

/** El tamaño con la unidad que se lee mejor (para `Intl.NumberFormat`). */
export function tamano(bytes: number): {
  readonly valor: number;
  readonly unidad: 'byte' | 'kilobyte' | 'megabyte' | 'gigabyte';
} {
  if (bytes >= 1024 ** 3) {
    return { valor: Math.round((bytes / 1024 ** 3) * 10) / 10, unidad: 'gigabyte' };
  }
  if (bytes >= 1024 ** 2) {
    return { valor: Math.round(bytes / 1024 ** 2), unidad: 'megabyte' };
  }
  if (bytes >= 1024) {
    return { valor: Math.round(bytes / 1024), unidad: 'kilobyte' };
  }
  return { valor: bytes, unidad: 'byte' };
}
