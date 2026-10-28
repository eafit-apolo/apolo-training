import type { ElementRef } from '@angular/core';
import {
  ChangeDetectionStrategy,
  Component,
  DOCUMENT,
  computed,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { Router } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { IdiomaService } from '../../core/i18n/idioma';
import { campoDeError, codigoDeError, estadoDeError } from '../../core/sesion/errores';
import { rutaInterna } from '../../core/sesion/rutas';
import { SesionService } from '../../core/sesion/sesion';
import { ErrorSi, valorDe } from '../../shared/error-si';
import { Icono } from '../../shared/icono';
import { plural } from '../../shared/plural';
import { CORREO_SOPORTE, desbloqueo, regionDe } from './hora';

/** Lo que salió mal al ingresar; cada uno tiene su texto en `errores.*`. */
type ErrorIngreso =
  | {
      readonly tipo:
        | 'clave_incorrecta'
        | 'cuenta_bloqueada_sin_hora'
        | 'cuenta_inactiva'
        | 'demasiadas_peticiones'
        | 'sin_conexion'
        | 'inesperado';
    }
  | { readonly tipo: 'cuenta_bloqueada'; readonly hasta: Date; readonly visto: Date };

/**
 * Pantalla 01, ingreso. Errores con el `codigo` de la API traducido; el
 * bloqueo dice hasta qué hora (con la zona) y cuántos minutos faltan. Nunca
 * dice cuántos intentos quedan: eso delataría qué usuarios existen (decisión
 * del 28-oct).
 */
@Component({
  selector: 'at-ingresar',
  imports: [MatButtonModule, MatFormFieldModule, MatInputModule, TranslocoPipe, Icono, ErrorSi],
  templateUrl: './ingresar.html',
  styleUrl: './cuenta.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Ingresar {
  /** `?volver=`: a dónde ir después de entrar (solo rutas internas). */
  readonly volver = input<string>();
  /** `?motivo=vencida`: el interceptor no pudo renovar la sesión. */
  readonly motivo = input<string>();

  private readonly sesion = inject(SesionService);
  private readonly router = inject(Router);
  private readonly idioma = inject(IdiomaService);
  private readonly documento = inject(DOCUMENT);
  private readonly campoClave = viewChild.required<ElementRef<HTMLInputElement>>('campoClave');

  protected readonly correo = CORREO_SOPORTE;
  protected readonly plural = plural;
  protected readonly ver = signal(false);
  protected readonly enviando = signal(false);
  protected readonly intento = signal(false);
  protected readonly error = signal<ErrorIngreso | null>(null);

  protected readonly valorDe = valorDe;
  protected readonly username = signal('');
  protected readonly clave = signal('');
  /** Los campos vacíos se marcan solo después de intentar enviar. */
  private readonly revisar = signal(false);
  protected readonly faltaUsuario = computed(() => this.revisar() && !this.username().trim());
  protected readonly faltaClave = computed(() => this.revisar() && !this.clave());

  /** «Tu sesión terminó», hasta el primer intento. */
  protected readonly vencida = computed(() => this.motivo() === 'vencida' && !this.intento());

  /** Hora y minutos del bloqueo, en el formato del idioma activo. */
  protected readonly bloqueo = computed(() => {
    const error = this.error();
    if (error?.tipo !== 'cuenta_bloqueada') {
      return null;
    }
    const preferidos = this.documento.defaultView?.navigator.languages ?? [];
    return desbloqueo(error.hasta, error.visto, regionDe(this.idioma.actual(), preferidos));
  });

  protected async enviar(evento: Event): Promise<void> {
    evento.preventDefault();
    if (this.enviando()) {
      return;
    }
    this.revisar.set(true);
    if (this.faltaUsuario() || this.faltaClave()) {
      return;
    }
    this.intento.set(true);
    this.error.set(null);
    this.enviando.set(true);
    try {
      // Los usuarios de Apolo van en minúsculas y sin espacios (patrón de la API).
      const usuario = await this.sesion.ingresar(
        this.username().trim().toLowerCase(),
        this.clave(),
      );
      const volver = rutaInterna(this.volver());
      if (usuario.debe_cambiar_clave) {
        await this.router.navigate(['/cambiar-clave'], volver ? { queryParams: { volver } } : {});
      } else {
        await this.router.navigateByUrl(volver ?? '/cursos');
      }
    } catch (error) {
      this.error.set(leerError(error));
      this.clave.set('');
      this.revisar.set(false);
      this.campoClave().nativeElement.focus();
    } finally {
      this.enviando.set(false);
    }
  }
}

function leerError(error: unknown): ErrorIngreso {
  if (estadoDeError(error) === 0) {
    return { tipo: 'sin_conexion' };
  }
  switch (codigoDeError(error)) {
    // Un usuario con mayúsculas raras o caracteres que la API no acepta (422)
    // recibe lo mismo que una clave errada.
    case 'clave_incorrecta':
    case 'datos_invalidos':
      return { tipo: 'clave_incorrecta' };
    case 'cuenta_bloqueada': {
      const hasta = new Date(String(campoDeError(error, 'bloqueado_hasta')));
      return Number.isNaN(hasta.getTime())
        ? { tipo: 'cuenta_bloqueada_sin_hora' }
        : { tipo: 'cuenta_bloqueada', hasta, visto: new Date() };
    }
    case 'cuenta_inactiva':
      return { tipo: 'cuenta_inactiva' };
    case 'demasiadas_peticiones':
      return { tipo: 'demasiadas_peticiones' };
    default:
      return { tipo: 'inesperado' };
  }
}
