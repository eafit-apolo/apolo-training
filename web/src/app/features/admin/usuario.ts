import {
  ChangeDetectionStrategy,
  Component,
  ViewEncapsulation,
  computed,
  effect,
  inject,
  input,
  signal,
  untracked,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { TranslocoPipe, TranslocoService } from '@jsverse/transloco';
import type { Idioma } from '../../core/i18n/idioma';
import { IdiomaService } from '../../core/i18n/idioma';
import { estadoDeError } from '../../core/sesion/errores';
import { SesionService } from '../../core/sesion/sesion';
import { Icono } from '../../shared/icono';
import type { Practica } from '../cursos/datos/api';
import { cifrasDe } from '../progreso/datos';
import { FormatoFecha } from '../progreso/formato';
import { ModulosProgreso } from '../progreso/modulos';
import type { Resultado } from './acciones';
import { AccionesUsuario } from './acciones';
import type { UsuarioDetalleApi } from './datos';
import { AdminApi } from './datos';

/** Un aviso: clave de traducción y parámetros. */
interface Texto {
  readonly clave: string;
  readonly parametros?: Record<string, unknown>;
}

/**
 * La página de un usuario en la administración (F-08, decisión del 27-nov):
 * los datos de su cuenta, sus acciones (reiniciar la clave de la plataforma y
 * cambiar el rol) y su Mi progreso en modo lectura: cifras, módulos (el mismo
 * componente de la F-07), las siete prácticas y la graduación. Sirve para
 * atender «no puedo entrar» o «no me aparece la práctica» sin abrir la base.
 */
@Component({
  selector: 'at-admin-usuario',
  imports: [
    MatButtonModule,
    MatProgressBarModule,
    RouterLink,
    TranslocoPipe,
    Icono,
    ModulosProgreso,
  ],
  templateUrl: './usuario.html',
  styleUrl: './usuario.scss',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UsuarioAdmin {
  private readonly api = inject(AdminApi);
  private readonly acciones = inject(AccionesUsuario);
  private readonly sesion = inject(SesionService);
  private readonly idioma = inject(IdiomaService).actual;
  private readonly formato = inject(FormatoFecha);
  private readonly transloco = inject(TranslocoService);

  /** El `:usuario` de la ruta. */
  readonly usuario = input.required<string>();

  protected readonly datos = signal<UsuarioDetalleApi | null>(null);
  protected readonly noExiste = signal(false);
  protected readonly fallo = signal(false);
  protected readonly aviso = signal<Texto | null>(null);
  protected readonly error = signal<string | null>(null);

  protected readonly cifras = computed(() => {
    const d = this.datos();
    return d ? cifrasDe(d.progreso) : null;
  });

  private pedido = 0;

  constructor() {
    effect(() => {
      const usuario = this.usuario();
      const idioma = this.idioma();
      untracked(() => void this.cargar(usuario, idioma));
    });
  }

  protected async reiniciar(): Promise<void> {
    const d = this.datos();
    if (!d) {
      return;
    }
    this.limpiar();
    await this.despues(await this.acciones.reiniciarClave(d), {
      clave: 'admin.clave.hecha',
      parametros: { username: d.username },
    });
  }

  protected async cambiarRol(): Promise<void> {
    const d = this.datos();
    if (!d) {
      return;
    }
    this.limpiar();
    const cambiado = await this.acciones.cambiarRol(d);
    if (cambiado) {
      if (this.sesion.rol() !== 'admin') {
        return; // Se quitó a sí mismo el rol: ya salió de la administración.
      }
      await this.despues(
        { tipo: 'hecho' },
        {
          clave: 'admin.rol.hecho',
          parametros: {
            username: cambiado.username,
            rol: this.transloco.translate(`admin.roles.${cambiado.rol}`),
          },
        },
      );
    }
  }

  protected reintentar(): void {
    void this.cargar(this.usuario(), this.idioma());
  }

  protected fecha(iso: string): string {
    return this.formato.fecha(iso);
  }

  protected hora(iso: string): string {
    return this.formato.hora(iso, Date.now());
  }

  protected nombreLab(lab: Practica): string {
    return `progreso.practicas.nombres.${lab}`;
  }

  private limpiar(): void {
    this.aviso.set(null);
    this.error.set(null);
  }

  private async despues(resultado: Resultado, hecho: Texto): Promise<void> {
    if (resultado.tipo === 'hecho') {
      this.aviso.set(hecho);
      await this.cargar(this.usuario(), this.idioma());
    } else if (resultado.tipo === 'error') {
      this.error.set(resultado.clave);
    }
  }

  private async cargar(usuario: string, idioma: Idioma): Promise<void> {
    const pedido = ++this.pedido;
    try {
      const datos = await this.api.usuario(usuario, idioma);
      if (pedido === this.pedido) {
        this.datos.set(datos);
        this.noExiste.set(false);
        this.fallo.set(false);
      }
    } catch (error) {
      if (pedido !== this.pedido) {
        return;
      }
      if (estadoDeError(error) === 404) {
        this.datos.set(null);
        this.noExiste.set(true);
      } else {
        this.fallo.set(true);
      }
    }
  }
}
