import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import type { Idioma } from '../../../core/i18n/idioma';
import { API } from '../../../core/sesion/sesion';

// Esquemas de api/openapi.yaml que usa la web (B-04). Los nombres de los campos
// son los de la API; `armarCurso()` los pasa a los tipos de las pantallas.

export type EstadoModuloApi = 'completo' | 'en_curso' | 'bloqueado';
export type Componente = 'video' | 'lectura' | 'practica' | 'quiz';

export interface ModuloRefApi {
  readonly id: number;
  readonly slug: string;
  readonly numero: number;
  readonly titulo: string;
}

export interface LeccionRefApi {
  readonly id: number;
  readonly slug: string;
  /** Slug del módulo (`m05`). */
  readonly modulo: string;
  readonly modulo_numero: number;
  readonly titulo: string;
}

export interface LeccionResumenApi {
  readonly id: number;
  readonly slug: string;
  readonly orden: number;
  readonly titulo: string;
  readonly duracion_min: number;
  readonly completada: boolean;
  readonly componentes: readonly Componente[];
}

export interface ModuloApi {
  readonly id: number;
  readonly slug: string;
  readonly numero: number;
  readonly titulo: string;
  readonly resumen: string;
  readonly duracion_min: number;
  readonly estado: EstadoModuloApi;
  readonly bloqueado_por: ModuloRefApi | null;
  readonly lecciones_total: number;
  readonly lecciones_completas: number;
  readonly videos: number;
  readonly practicas: number;
  readonly preguntas: number;
  readonly componentes: readonly Componente[];
  readonly lecciones: readonly LeccionResumenApi[];
}

export interface CursoResumenApi {
  readonly id: number;
  readonly slug: string;
  readonly titulo: string;
  readonly descripcion: string | null;
  readonly duracion_min: number;
  readonly videos: number;
  readonly avance_pct: number;
  readonly modulos_total: number;
  readonly modulos_completos: number;
  readonly lecciones_total: number;
  readonly lecciones_completas: number;
  readonly continuar: LeccionRefApi | null;
  readonly fallback: boolean;
}

export interface CursoDetalleApi extends CursoResumenApi {
  readonly modulos: readonly ModuloApi[];
}

/** Las siete prácticas del verificador (`apolo-training verificar <práctica>`). */
export type Practica =
  'conexion' | 'terminal' | 'archivos' | 'modulos' | 'memoria' | 'nucleos' | 'paralelo';

/** `todos`, o un sistema operativo en la lección de VPN. */
export type SistemaVideo = 'todos' | 'windows' | 'macos' | 'linux';

export interface VideoRefApi {
  readonly id: number;
  readonly clave: string;
  /** `false` mientras no se haya subido el MP4 («Video en preparación»). */
  readonly disponible: boolean;
  readonly duracion_seg: number | null;
  readonly url: string | null;
  readonly subtitulos: readonly { readonly idioma: Idioma; readonly url: string }[];
}

export interface VideoLeccionApi {
  readonly sistema: SistemaVideo;
  readonly video: VideoRefApi;
}

export interface ProgresoLeccionApi {
  readonly leccion_id: number;
  readonly video_posicion_seg: number;
  readonly video_max_seg: number;
  readonly video_completo: boolean;
  readonly quiz_aprobado: boolean;
  readonly completada: boolean;
  readonly completada_en: string | null;
}

/** Esquema `Leccion`: el cuerpo de la lección (F-04). */
export interface LeccionApi {
  readonly id: number;
  readonly slug: string;
  readonly curso: string;
  readonly modulo: ModuloRefApi;
  readonly orden: number;
  readonly titulo: string;
  /** Markdown con pestañas `::: apolo2` / `::: apolo3` (C-01). */
  readonly contenido: string;
  /** No hay traducción: el contenido viene en español. */
  readonly fallback: boolean;
  readonly duracion_min: number;
  readonly componentes: readonly Componente[];
  readonly videos: readonly VideoLeccionApi[];
  readonly practicas: readonly Practica[];
  readonly quiz_id: number | null;
  /** También entre módulos; si el de la siguiente está bloqueado, lo dice el catálogo. */
  readonly anterior: LeccionRefApi | null;
  readonly siguiente: LeccionRefApi | null;
  readonly progreso: ProgresoLeccionApi;
}

/**
 * Las rutas de lectura de contenido (`GET /api/cursos…`). Va aparte de
 * `CatalogoService` para que las pruebas la reemplacen por datos de ejemplo.
 */
@Injectable({ providedIn: 'root' })
export class ContenidoApi {
  private readonly http = inject(HttpClient);

  cursos(idioma: Idioma): Promise<CursoResumenApi[]> {
    return firstValueFrom(
      this.http.get<CursoResumenApi[]>(`${API}/cursos`, { params: { lang: idioma } }),
    );
  }

  /** El curso con sus módulos y lecciones; `null` si no existe (404). */
  async curso(slug: string, idioma: Idioma): Promise<CursoDetalleApi | null> {
    try {
      return await firstValueFrom(
        this.http.get<CursoDetalleApi>(`${API}/cursos/${encodeURIComponent(slug)}`, {
          params: { lang: idioma },
        }),
      );
    } catch (error) {
      if (error instanceof HttpErrorResponse && error.status === 404) {
        return null;
      }
      throw error;
    }
  }

  /**
   * Una lección; `null` si no existe (404). Un estudiante en un módulo
   * bloqueado recibe 403 `modulo_bloqueado`, que sale como error.
   */
  async leccion(
    curso: string,
    modulo: string,
    leccion: string,
    idioma: Idioma,
  ): Promise<LeccionApi | null> {
    const ruta = [curso, 'lecciones', modulo, leccion].map(encodeURIComponent).join('/');
    try {
      return await firstValueFrom(
        this.http.get<LeccionApi>(`${API}/cursos/${ruta}`, { params: { lang: idioma } }),
      );
    } catch (error) {
      if (error instanceof HttpErrorResponse && error.status === 404) {
        return null;
      }
      throw error;
    }
  }

  /**
   * `POST /api/lecciones/{id}/completar` (el interceptor pone el CSRF). 409
   * `requisitos_pendientes` si tiene un video subido sin ver.
   */
  completar(leccionId: number): Promise<ProgresoLeccionApi> {
    return firstValueFrom(
      this.http.post<ProgresoLeccionApi>(`${API}/lecciones/${leccionId}/completar`, null),
    );
  }
}
