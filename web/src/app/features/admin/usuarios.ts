import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ViewEncapsulation,
  computed,
  effect,
  inject,
  signal,
  untracked,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { TranslocoPipe, TranslocoService } from '@jsverse/transloco';
import type { Cluster, Rol } from '../../core/sesion/sesion';
import { SesionService } from '../../core/sesion/sesion';
import { Icono } from '../../shared/icono';
import { FormatoFecha } from '../progreso/formato';
import type { Resultado } from './acciones';
import { AccionesUsuario } from './acciones';
import type { EstadoCuenta, FiltrosUsuarios, ListaUsuariosApi, UsuarioAdminApi } from './datos';
import { AdminApi, CLUSTERES, ESTADOS_CUENTA, ROLES } from './datos';

/** Cuánto se espera tras la última tecla antes de buscar. */
const ESPERA_MS = 300;

/** Un aviso: clave de traducción y parámetros. */
interface Texto {
  readonly clave: string;
  readonly parametros?: Record<string, unknown>;
}

/**
 * Pestaña «Usuarios» de la administración (F-08): búsqueda por usuario,
 * nombre o correo, filtros por clúster, rol y estado de la cuenta, y 50 por
 * página. Cada fila lleva a la página del usuario y tiene sus acciones
 * (reiniciar la clave de la plataforma y cambiar el rol). «Nuevo usuario»
 * solo muestra la orden para la VM de práctica.
 */
@Component({
  selector: 'at-admin-usuarios',
  imports: [MatButtonModule, MatMenuModule, MatProgressBarModule, RouterLink, TranslocoPipe, Icono],
  templateUrl: './usuarios.html',
  styleUrl: './usuarios.scss',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UsuariosAdmin {
  private readonly api = inject(AdminApi);
  private readonly acciones = inject(AccionesUsuario);
  private readonly sesion = inject(SesionService);
  private readonly formato = inject(FormatoFecha);
  private readonly transloco = inject(TranslocoService);

  protected readonly clusteres = CLUSTERES;
  protected readonly roles = ROLES;
  protected readonly estados = ESTADOS_CUENTA;

  /** Lo escrito en la búsqueda; `q` es lo que se buscó (tras la espera). */
  protected readonly escrito = signal('');
  private readonly q = signal('');
  protected readonly cluster = signal<Cluster | null>(null);
  protected readonly rol = signal<Rol | null>(null);
  protected readonly estado = signal<EstadoCuenta | null>(null);
  protected readonly pagina = signal(1);

  protected readonly lista = signal<ListaUsuariosApi | null>(null);
  protected readonly fallo = signal(false);
  protected readonly aviso = signal<Texto | null>(null);
  protected readonly error = signal<string | null>(null);

  private readonly filtros = computed<FiltrosUsuarios>(
    () => ({
      q: this.q(),
      cluster: this.cluster(),
      rol: this.rol(),
      estado: this.estado(),
      pagina: this.pagina(),
    }),
    { equal: (a, b) => JSON.stringify(a) === JSON.stringify(b) },
  );

  protected readonly conFiltros = computed(() => {
    const f = this.filtros();
    return Boolean(f.q.trim() || f.cluster || f.rol || f.estado);
  });

  /** «1–50 de 124». */
  protected readonly rango = computed(() => {
    const l = this.lista();
    if (!l || !l.total) {
      return null;
    }
    const desde = (l.pagina - 1) * l.por_pagina + 1;
    return { desde, hasta: desde + l.items.length - 1, total: l.total };
  });
  protected readonly hayAnterior = computed(() => (this.lista()?.pagina ?? 1) > 1);
  protected readonly haySiguiente = computed(() => {
    const r = this.rango();
    return r !== null && r.hasta < r.total;
  });

  private temporizador: ReturnType<typeof setTimeout> | undefined;
  private pedido = 0;

  constructor() {
    effect(() => {
      const filtros = this.filtros();
      untracked(() => void this.cargar(filtros));
    });
    inject(DestroyRef).onDestroy(() => clearTimeout(this.temporizador));
  }

  protected escribir(valor: string): void {
    this.escrito.set(valor);
    clearTimeout(this.temporizador);
    this.temporizador = setTimeout(() => {
      this.pagina.set(1);
      this.q.set(valor);
    }, ESPERA_MS);
  }

  protected elegirCluster(valor: string): void {
    this.pagina.set(1);
    this.cluster.set(this.clusteres.find((c) => c === valor) ?? null);
  }

  protected elegirRol(valor: string): void {
    this.pagina.set(1);
    this.rol.set(this.roles.find((r) => r === valor) ?? null);
  }

  protected elegirEstado(valor: string): void {
    this.pagina.set(1);
    this.estado.set(this.estados.find((e) => e === valor) ?? null);
  }

  protected irA(pagina: number): void {
    this.pagina.set(Math.max(1, pagina));
  }

  protected nuevo(): void {
    this.acciones.nuevoUsuario();
  }

  protected async reiniciar(usuario: UsuarioAdminApi): Promise<void> {
    this.limpiarAvisos();
    this.mostrar(await this.acciones.reiniciarClave(usuario), {
      clave: 'admin.clave.hecha',
      parametros: { username: usuario.username },
    });
  }

  protected async cambiarRol(usuario: UsuarioAdminApi): Promise<void> {
    this.limpiarAvisos();
    const cambiado = await this.acciones.cambiarRol(usuario);
    if (cambiado) {
      if (this.sesion.rol() !== 'admin') {
        return; // Se quitó a sí mismo el rol: ya salió de la administración.
      }
      this.mostrar(
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
    void this.cargar(this.filtros());
  }

  protected hora(iso: string): string {
    return this.formato.hora(iso, Date.now());
  }

  protected fecha(iso: string): string {
    return this.formato.fecha(iso);
  }

  private limpiarAvisos(): void {
    this.aviso.set(null);
    this.error.set(null);
  }

  /** Tras una acción: el aviso o el error, y la lista otra vez (cambia el estado). */
  private mostrar(resultado: Resultado, hecho: Texto): void {
    if (resultado.tipo === 'hecho') {
      this.aviso.set(hecho);
      void this.cargar(this.filtros());
    } else if (resultado.tipo === 'error') {
      this.error.set(resultado.clave);
    }
  }

  private async cargar(filtros: FiltrosUsuarios): Promise<void> {
    const pedido = ++this.pedido;
    try {
      const lista = await this.api.usuarios(filtros);
      if (pedido === this.pedido) {
        this.lista.set(lista);
        this.fallo.set(false);
      }
    } catch {
      if (pedido === this.pedido) {
        this.fallo.set(true);
      }
    }
  }
}
