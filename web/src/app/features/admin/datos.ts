import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import type { Idioma } from '../../core/i18n/idioma';
import type { Cluster, Rol, Usuario } from '../../core/sesion/sesion';
import { API } from '../../core/sesion/sesion';
import type { EstadoGraduacion, MiProgresoApi } from '../progreso/datos';

// Esquemas del grupo `admin` de api/openapi.yaml (solo admin, B-08):
// `UsuarioAdmin`, `UsuarioDetalleAdmin`, `ListaUsuarios`, `ClaveTemporal` y
// `AprobadoPendiente`.

/** Uno solo por cuenta: gana el primero que se cumple, en este orden. */
export type EstadoCuenta = 'baja' | 'bloqueado' | 'debe_cambiar_clave' | 'activo';
export const ESTADOS_CUENTA: readonly EstadoCuenta[] = [
  'activo',
  'debe_cambiar_clave',
  'bloqueado',
  'baja',
];
export const ROLES: readonly Rol[] = ['estudiante', 'instructor', 'admin'];
export const CLUSTERES: readonly Cluster[] = ['apolo2', 'apolo3'];

export interface UsuarioAdminApi extends Usuario {
  readonly estado: EstadoCuenta;
  readonly bloqueado_hasta: string | null;
  readonly creado_en: string;
  readonly ultimo_ingreso: string | null;
  readonly baja_en: string | null;
  readonly avance_pct: number;
  readonly labs_aprobados: number;
  readonly graduacion_estado: EstadoGraduacion | null;
}

export interface UsuarioDetalleApi extends UsuarioAdminApi {
  /** Su Mi progreso (la pantalla 04 en modo lectura). */
  readonly progreso: MiProgresoApi;
}

export interface ListaUsuariosApi {
  readonly total: number;
  readonly pagina: number;
  readonly por_pagina: number;
  readonly items: readonly UsuarioAdminApi[];
}

export interface ClaveTemporalApi {
  readonly username: string;
  readonly clave_temporal: string;
}

export interface AprobadoPendienteApi {
  readonly username: string;
  readonly nombre: string;
  readonly cluster: Cluster;
  /** Cuándo se cumplió la última de las tres condiciones. */
  readonly aprobado_en: string;
}

export interface FiltrosUsuarios {
  readonly q: string;
  readonly cluster: Cluster | null;
  readonly rol: Rol | null;
  readonly estado: EstadoCuenta | null;
  readonly pagina: number;
}

/** Usuarios por página en la lista. */
export const POR_PAGINA = 50;

/** El grupo `admin` de la API. */
@Injectable({ providedIn: 'root' })
export class AdminApi {
  private readonly http = inject(HttpClient);

  usuarios(filtros: FiltrosUsuarios): Promise<ListaUsuariosApi> {
    const params: Record<string, string | number> = {
      pagina: filtros.pagina,
      por_pagina: POR_PAGINA,
    };
    const q = filtros.q.trim();
    if (q) {
      params['q'] = q;
    }
    if (filtros.cluster) {
      params['cluster'] = filtros.cluster;
    }
    if (filtros.rol) {
      params['rol'] = filtros.rol;
    }
    if (filtros.estado) {
      params['estado'] = filtros.estado;
    }
    return firstValueFrom(this.http.get<ListaUsuariosApi>(`${API}/admin/usuarios`, { params }));
  }

  /** `?lang=`: la web cambia el idioma antes de que termine el `PATCH /me`. 404 si no existe. */
  usuario(username: string, idioma: Idioma): Promise<UsuarioDetalleApi> {
    return firstValueFrom(
      this.http.get<UsuarioDetalleApi>(`${API}/admin/usuarios/${encodeURIComponent(username)}`, {
        params: { lang: idioma },
      }),
    );
  }

  /** 409 `ultimo_admin` si quitaría al último admin activo. */
  cambiarRol(username: string, rol: Rol): Promise<UsuarioAdminApi> {
    return firstValueFrom(
      this.http.patch<UsuarioAdminApi>(`${API}/admin/usuarios/${encodeURIComponent(username)}`, {
        rol,
      }),
    );
  }

  /** La clave temporal se ve una sola vez. 409 `usuario_inactivo` con una baja. */
  reiniciarClave(username: string): Promise<ClaveTemporalApi> {
    return firstValueFrom(
      this.http.post<ClaveTemporalApi>(
        `${API}/admin/usuarios/${encodeURIComponent(username)}/reiniciar-clave`,
        null,
      ),
    );
  }

  pendientes(): Promise<AprobadoPendienteApi[]> {
    return firstValueFrom(
      this.http.get<AprobadoPendienteApi[]>(`${API}/admin/aprobados-pendientes`),
    );
  }

  /** 204; 409 `qos_ya_aplicada` o `no_aprobado`. */
  async marcarQos(username: string): Promise<void> {
    await firstValueFrom(
      this.http.post<null>(
        `${API}/admin/aprobados-pendientes/${encodeURIComponent(username)}/qos-aplicada`,
        null,
      ),
    );
  }
}

// --- «Nuevo usuario»: la orden para la VM de práctica ----------------------------

/** Las mismas reglas de `apolo-training-admin` (V-04) y de la API. */
export const PATRON_USUARIO = /^[a-z_][a-z0-9_-]{0,31}$/;
export const PATRON_CORREO = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
export const NOMBRE_MAXIMO = 120;
export const CORREO_MAXIMO = 254;

export interface DatosAlta {
  readonly usuario: string;
  readonly nombre: string;
  readonly correo: string;
  readonly cluster: Cluster;
  readonly idioma: Idioma;
}

export type FaltaAlta =
  'usuario' | 'usuarioInvalido' | 'nombre' | 'nombreInvalido' | 'correo' | 'correoInvalido';

/** Lo que falta para armar la orden; vacío = lista para copiar. */
export function faltasAlta(datos: DatosAlta): readonly FaltaAlta[] {
  const faltas: FaltaAlta[] = [];
  const usuario = datos.usuario.trim();
  if (!usuario) {
    faltas.push('usuario');
  } else if (!PATRON_USUARIO.test(usuario)) {
    faltas.push('usuarioInvalido');
  }
  const nombre = datos.nombre.trim();
  if (!nombre) {
    faltas.push('nombre');
  } else if ([...nombre].length > NOMBRE_MAXIMO || /[:,\n]/.test(nombre)) {
    // Va también al campo GECOS de /etc/passwd, que separa con : y ,
    faltas.push('nombreInvalido');
  }
  const correo = datos.correo.trim();
  if (!correo) {
    faltas.push('correo');
  } else if (correo.length > CORREO_MAXIMO || !PATRON_CORREO.test(correo)) {
    faltas.push('correoInvalido');
  }
  return faltas;
}

/**
 * Un argumento de shell: tal cual si es seguro y, si no, entre comillas
 * simples (una comilla simple adentro se escribe `'\''`).
 */
export function comillas(texto: string): string {
  return /^[A-Za-z0-9@%+=.,/_:-]+$/.test(texto) ? texto : `'${texto.replace(/'/g, `'\\''`)}'`;
}

/** La orden de alta, lista para pegar en la VM como admin (con sudo). */
export function ordenAlta(datos: DatosAlta): string {
  const partes = [
    'sudo apolo-training-admin alta',
    comillas(datos.usuario.trim()),
    `--cluster ${datos.cluster}`,
    `--nombre ${comillas(datos.nombre.trim())}`,
    `--correo ${comillas(datos.correo.trim())}`,
  ];
  if (datos.idioma === 'en') {
    partes.push('--idioma en');
  }
  return partes.join(' ');
}

// --- QOS ---------------------------------------------------------------------------

/**
 * El nombre de la QOS normal de cada clúster lo define la V-08 (coordinación);
 * mientras tanto va este marcador. Cambiarlo aquí cuando esté decidido.
 */
export const QOS_NORMAL = '<qos-normal>';

export function comandoQos(username: string): string {
  return `sacctmgr modify user ${username} set qos=${QOS_NORMAL}`;
}
