import type { Provider } from '@angular/core';
import { MATERIAL_ANIMATIONS } from '@angular/material/core';
import type {
  GraduacionAdminApi,
  ResumenPanelApi,
  VideoAdminApi,
} from '../app/features/panel/datos';
import { CREAR_XHR } from '../app/features/panel/subidas';

// Datos de ejemplo del panel de instructor (F-08), con la forma de la API.

export function resumenDeEjemplo(mas: Partial<ResumenPanelApi> = {}): ResumenPanelApi {
  return {
    estudiantes_activos: 8,
    sin_empezar: 1,
    en_curso: 6,
    aprobados: 1,
    graduaciones_por_revisar: 2,
    aprobados_pendientes_qos: 1,
    ultima_sincronizacion: new Date(Date.now() - 2 * 60_000).toISOString(),
    avance_por_modulo: [
      { numero: 0, titulo: 'Bienvenida', completos: 7 },
      { numero: 1, titulo: 'Conexión', completos: 6 },
      { numero: 2, titulo: 'Terminal y Linux', completos: 3 },
    ],
    ...mas,
  };
}

export function graduacionAdminDeEjemplo(
  mas: Partial<GraduacionAdminApi> = {},
): GraduacionAdminApi {
  return {
    username: 'ana',
    nombre: 'Ana Ejemplo',
    cluster: 'apolo2',
    jobid: '55120',
    salida_verificador: '[APROBADO] graduacion · Apolo II · job 55120',
    estado: 'enviada',
    enviada_en: '2026-11-26T15:00:00Z',
    revisada_en: null,
    revisada_por: null,
    comentario: null,
    qos_aplicada_en: null,
    labs_aprobados: 7,
    ...mas,
  };
}

export function videoDeEjemplo(mas: Partial<VideoAdminApi> = {}): VideoAdminApi {
  return {
    id: 1,
    clave: 'm00-bienvenida',
    disponible: false,
    duracion_seg: null,
    tamano_bytes: null,
    subtitulos: { es: false, en: false },
    lecciones: [
      {
        id: 10,
        slug: 'bienvenida',
        modulo: 'm00',
        modulo_numero: 0,
        titulo: 'Bienvenida al curso',
      },
    ],
    subido_por: null,
    subido_en: null,
    ...mas,
  };
}

/** Sin animaciones: los diálogos de Material abren y cierran sin esperar. */
export function sinAnimaciones(): Provider {
  return { provide: MATERIAL_ANIMATIONS, useValue: { animationsDisabled: true } };
}

/**
 * Un `XMLHttpRequest` de mentira para las subidas: guarda lo que hizo la app
 * (método, URL, cabeceras, cuerpo) y simula el progreso y la respuesta.
 */
export class XhrDePrueba {
  metodo = '';
  url = '';
  readonly cabeceras: Record<string, string> = {};
  cuerpo: unknown = null;
  abortado = false;
  readyState = 1;
  status = 0;
  statusText = '';
  responseText = '';
  readonly upload: { onprogress: ((evento: ProgressEvent) => void) | null } = {
    onprogress: null,
  };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;

  open(metodo: string, url: string): void {
    this.metodo = metodo;
    this.url = url;
  }

  setRequestHeader(nombre: string, valor: string): void {
    this.cabeceras[nombre] = valor;
  }

  send(cuerpo: unknown): void {
    this.cuerpo = cuerpo;
  }

  abort(): void {
    this.abortado = true;
  }

  // Lo que hace el servidor.

  progreso(cargado: number, total: number): void {
    this.upload.onprogress?.({ loaded: cargado, total, lengthComputable: true } as ProgressEvent);
  }

  responder(status: number, cuerpo: unknown): void {
    this.readyState = 4;
    this.status = status;
    this.responseText = cuerpo === null ? '' : JSON.stringify(cuerpo);
    this.onload?.();
  }

  sinRed(): void {
    this.readyState = 4;
    this.onerror?.();
  }
}

/** Reemplaza el XHR de las subidas; `xhrs` guarda cada uno que crea la app. */
export function simularSubidas(): { readonly proveedor: Provider; readonly xhrs: XhrDePrueba[] } {
  const xhrs: XhrDePrueba[] = [];
  return {
    xhrs,
    proveedor: {
      provide: CREAR_XHR,
      useValue: () => {
        const xhr = new XhrDePrueba();
        xhrs.push(xhr);
        return xhr as unknown as XMLHttpRequest;
      },
    },
  };
}
