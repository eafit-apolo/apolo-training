import { Injectable, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { codigoDeError, estadoDeError } from '../../core/sesion/errores';
import { SesionService } from '../../core/sesion/sesion';
import { confirmar } from '../../shared/confirmar';
import type { DatosCambiarRol } from './cambiar-rol';
import { CambiarRolDialogo } from './cambiar-rol';
import { ClaveTemporalDialogo } from './clave-temporal';
import type { ClaveTemporalApi, UsuarioAdminApi } from './datos';
import { AdminApi } from './datos';
import { NuevoUsuarioDialogo } from './nuevo-usuario';

/** Cómo terminó una acción: hecha, cancelada o con un error (clave de traducción). */
export type Resultado =
  | { readonly tipo: 'hecho' }
  | { readonly tipo: 'cancelado' }
  | { readonly tipo: 'error'; readonly clave: string };

/**
 * Las acciones sobre una cuenta, iguales en la lista de usuarios y en la
 * página de cada uno (pantalla 06): reiniciar la clave de la plataforma,
 * cambiar el rol y «Nuevo usuario».
 */
@Injectable({ providedIn: 'root' })
export class AccionesUsuario {
  private readonly api = inject(AdminApi);
  private readonly dialogo = inject(MatDialog);
  private readonly sesion = inject(SesionService);
  private readonly router = inject(Router);

  /**
   * Pregunta (cierra sus sesiones y le pide cambiarla al entrar), reinicia y
   * muestra la clave temporal una sola vez.
   */
  async reiniciarClave(usuario: Pick<UsuarioAdminApi, 'username' | 'nombre'>): Promise<Resultado> {
    const seguro = await confirmar(this.dialogo, {
      titulo: 'admin.clave.preguntaTitulo',
      mensaje: 'admin.clave.pregunta',
      confirmar: 'admin.clave.confirmar',
      parametros: { username: usuario.username, nombre: usuario.nombre },
    });
    if (!seguro) {
      return { tipo: 'cancelado' };
    }
    let clave: ClaveTemporalApi;
    try {
      clave = await this.api.reiniciarClave(usuario.username);
    } catch (error) {
      const codigo = codigoDeError(error);
      return {
        tipo: 'error',
        clave:
          codigo === 'usuario_inactivo'
            ? 'admin.clave.inactivo'
            : codigo === 'no_encontrado'
              ? 'admin.noExiste'
              : estadoDeError(error) === 0
                ? 'errores.sin_conexion'
                : 'errores.inesperado',
      };
    }
    const ref = this.dialogo.open(ClaveTemporalDialogo, {
      data: clave,
      width: '32rem',
      maxWidth: 'calc(100vw - 32px)',
      // Que no se cierre por un clic afuera sin haberla copiado.
      disableClose: true,
    });
    await firstValueFrom(ref.afterClosed());
    return { tipo: 'hecho' };
  }

  /**
   * El usuario con el rol nuevo, o `null` si se canceló. Si el admin se quitó
   * a sí mismo el rol, se vuelve a leer su perfil (`GET /api/me`) y sale de
   * Administración, que ya no puede ver.
   */
  async cambiarRol(usuario: UsuarioAdminApi): Promise<UsuarioAdminApi | null> {
    const propio = usuario.username === this.sesion.usuario()?.username;
    const ref = this.dialogo.open<CambiarRolDialogo, DatosCambiarRol, UsuarioAdminApi>(
      CambiarRolDialogo,
      {
        data: { username: usuario.username, nombre: usuario.nombre, rol: usuario.rol, propio },
        width: '30rem',
        maxWidth: 'calc(100vw - 32px)',
      },
    );
    const cambiado = (await firstValueFrom(ref.afterClosed())) ?? null;
    if (cambiado && propio && cambiado.rol !== 'admin') {
      await this.sesion.iniciar();
      await this.router.navigateByUrl('/cursos');
    }
    return cambiado;
  }

  nuevoUsuario(): void {
    this.dialogo.open(NuevoUsuarioDialogo, {
      width: '36rem',
      maxWidth: 'calc(100vw - 32px)',
    });
  }
}
