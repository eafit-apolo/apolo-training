import type { ElementRef, WritableSignal } from '@angular/core';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router, RouterLink } from '@angular/router';
import { TranslocoPipe, TranslocoService } from '@jsverse/transloco';
import { codigoDeError, estadoDeError } from '../../core/sesion/errores';
import { rutaInterna } from '../../core/sesion/rutas';
import { SesionService } from '../../core/sesion/sesion';
import { ErrorSi, valorDe } from '../../shared/error-si';
import { Icono } from '../../shared/icono';

/** La política de la B-03 (`CLAVE_MINIMA` y `CLAVE_MAXIMA` de la API). */
export const CLAVE_MINIMA = 8;
export const CLAVE_MAXIMA = 128;

export interface Regla {
  readonly clave: 'largo' | 'maximo' | 'distintaActual' | 'distintaUsuario' | 'coinciden';
  readonly ok: boolean;
}

/**
 * Las reglas que se marcan mientras se escribe. La API las vuelve a revisar
 * (`clave_debil`, `clave_repetida`). El largo se cuenta en caracteres, como
 * Python (`[...texto]`), no en unidades UTF-16: un emoji cuenta como uno.
 */
export function reglasDeClave(
  actual: string,
  nueva: string,
  repetir: string,
  username: string,
): readonly Regla[] {
  const largo = [...nueva].length;
  const hay = nueva !== '';
  const reglas: Regla[] = [
    { clave: 'largo', ok: largo >= CLAVE_MINIMA },
    { clave: 'distintaActual', ok: hay && nueva !== actual },
    { clave: 'distintaUsuario', ok: hay && nueva.toLowerCase() !== username.toLowerCase() },
    { clave: 'coinciden', ok: hay && nueva === repetir },
  ];
  // El máximo solo aparece si se pasa: casi nadie llega a 128.
  return largo > CLAVE_MAXIMA ? [...reglas, { clave: 'maximo', ok: false }] : reglas;
}

/**
 * Pantalla 01, cambio de contraseña. Obligatorio en el primer ingreso (y
 * después de un reinicio): sin menú y sin salida salvo «Cerrar sesión».
 * Voluntario desde el menú de usuario (decisión del 28-oct): pide la actual,
 * tiene «Cancelar» y avisa que cierra las sesiones en otros equipos.
 */
@Component({
  selector: 'at-cambiar-clave',
  imports: [
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    TranslocoPipe,
    Icono,
    ErrorSi,
  ],
  templateUrl: './cambiar-clave.html',
  styleUrl: './cuenta.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CambiarClave {
  /** `?volver=`: a dónde ir después (o al cancelar). */
  readonly volver = input<string>();

  private readonly sesion = inject(SesionService);
  private readonly router = inject(Router);
  private readonly transloco = inject(TranslocoService);
  private readonly avisos = inject(MatSnackBar);
  private readonly campoActual = viewChild.required<ElementRef<HTMLInputElement>>('campoActual');
  private readonly campoNueva = viewChild.required<ElementRef<HTMLInputElement>>('campoNueva');

  protected readonly obligatorio = computed(
    () => this.sesion.usuario()?.debe_cambiar_clave !== false,
  );
  protected readonly destino = computed(() => rutaInterna(this.volver()) ?? '/cursos');
  protected readonly ver = signal(false);
  protected readonly enviando = signal(false);
  /** Clave de `errores.*` o de `cuenta.cambiar.*` con lo que salió mal. */
  protected readonly error = signal<string | null>(null);

  protected readonly actual = signal('');
  protected readonly nueva = signal('');
  protected readonly repetir = signal('');
  private readonly revisar = signal(false);
  protected readonly faltaActual = computed(() => this.revisar() && !this.actual());

  protected readonly reglas = computed(() =>
    reglasDeClave(
      this.actual(),
      this.nueva(),
      this.repetir(),
      this.sesion.usuario()?.username ?? '',
    ),
  );

  /** Al corregir un campo, el error de la API ya no aplica: se quita. */
  protected escribir(campo: WritableSignal<string>, evento: Event): void {
    campo.set(valorDe(evento));
    this.error.set(null);
  }

  protected async enviar(evento: Event): Promise<void> {
    evento.preventDefault();
    if (this.enviando()) {
      return;
    }
    this.error.set(null);
    this.revisar.set(true);
    if (this.faltaActual()) {
      this.campoActual().nativeElement.focus();
      return;
    }
    if (this.reglas().some((r) => !r.ok)) {
      this.error.set('cuenta.cambiar.revisar');
      this.campoNueva().nativeElement.focus();
      return;
    }
    const eraObligatorio = this.obligatorio();
    this.enviando.set(true);
    try {
      await this.sesion.cambiarClave(this.actual(), this.nueva());
      if (!eraObligatorio) {
        this.avisos.open(this.transloco.translate('cuenta.cambiar.hecho'), undefined, {
          duration: 8000,
        });
      }
      await this.router.navigateByUrl(this.destino());
    } catch (error) {
      const clave = leerError(error, eraObligatorio);
      this.error.set(clave);
      if (
        clave === 'errores.clave_actual_incorrecta' ||
        clave === 'errores.clave_temporal_incorrecta'
      ) {
        this.actual.set('');
        this.revisar.set(false);
        this.campoActual().nativeElement.focus();
      } else {
        this.campoNueva().nativeElement.focus();
      }
    } finally {
      this.enviando.set(false);
    }
  }

  protected salir(): void {
    void this.sesion.salir();
  }
}

function leerError(error: unknown, obligatorio: boolean): string {
  if (estadoDeError(error) === 0) {
    return 'errores.sin_conexion';
  }
  switch (codigoDeError(error)) {
    case 'clave_incorrecta':
      return obligatorio ? 'errores.clave_temporal_incorrecta' : 'errores.clave_actual_incorrecta';
    case 'clave_debil':
      return 'errores.clave_debil';
    case 'clave_repetida':
      return 'errores.clave_repetida';
    case 'datos_invalidos':
      return 'errores.clave_larga';
    default:
      return 'errores.inesperado';
  }
}
