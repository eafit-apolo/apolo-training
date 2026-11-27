import type {
  AprobadoPendienteApi,
  ListaUsuariosApi,
  UsuarioAdminApi,
  UsuarioDetalleApi,
} from '../app/features/admin/datos';
import { progresoDeEjemplo } from './progreso';

// Datos de ejemplo de la administración (F-08), con la forma de la API (B-08).

export function usuarioAdminDeEjemplo(mas: Partial<UsuarioAdminApi> = {}): UsuarioAdminApi {
  return {
    username: 'ana',
    nombre: 'Ana Ejemplo',
    correo: 'ana@example.com',
    cluster: 'apolo3',
    rol: 'estudiante',
    idioma: 'es',
    debe_cambiar_clave: false,
    activo: true,
    estado: 'activo',
    bloqueado_hasta: null,
    creado_en: '2026-11-20T15:00:00Z',
    ultimo_ingreso: '2026-11-26T14:12:00Z',
    baja_en: null,
    avance_pct: 52,
    labs_aprobados: 3,
    graduacion_estado: null,
    ...mas,
  };
}

/** Seis cuentas, una de cada caso de la pantalla 06. */
export function usuariosDeEjemplo(): UsuarioAdminApi[] {
  return [
    usuarioAdminDeEjemplo(),
    usuarioAdminDeEjemplo({
      username: 'bruno',
      nombre: 'Bruno Ejemplo',
      cluster: 'apolo2',
      rol: 'instructor',
      avance_pct: 0,
    }),
    usuarioAdminDeEjemplo({
      username: 'diego',
      nombre: 'Diego Ejemplo',
      estado: 'bloqueado',
      bloqueado_hasta: '2026-11-27T15:45:00Z',
      avance_pct: 61,
    }),
    usuarioAdminDeEjemplo({
      username: 'felipe',
      nombre: 'Felipe Ejemplo',
      estado: 'debe_cambiar_clave',
      debe_cambiar_clave: true,
      avance_pct: 0,
      ultimo_ingreso: null,
    }),
    usuarioAdminDeEjemplo({
      username: 'gabriela',
      nombre: 'Gabriela Ejemplo',
      cluster: 'apolo2',
      estado: 'baja',
      activo: false,
      baja_en: '2026-11-25T15:00:00Z',
      avance_pct: 23,
    }),
    usuarioAdminDeEjemplo({
      username: 'elena',
      nombre: 'Elena Admin',
      rol: 'admin',
      avance_pct: 0,
    }),
  ];
}

export function listaDeEjemplo(
  items: readonly UsuarioAdminApi[] = usuariosDeEjemplo(),
  mas: Partial<ListaUsuariosApi> = {},
): ListaUsuariosApi {
  return { total: items.length, pagina: 1, por_pagina: 50, items, ...mas };
}

export function detalleDeEjemplo(mas: Partial<UsuarioDetalleApi> = {}): UsuarioDetalleApi {
  return { ...usuarioAdminDeEjemplo(), progreso: progresoDeEjemplo(), ...mas };
}

export function aprobadoDeEjemplo(mas: Partial<AprobadoPendienteApi> = {}): AprobadoPendienteApi {
  return {
    username: 'carla',
    nombre: 'Carla Ejemplo',
    cluster: 'apolo2',
    aprobado_en: '2026-11-26T15:00:00Z',
    ...mas,
  };
}
