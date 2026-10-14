import { Injectable, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Title } from '@angular/platform-browser';
import type { RouterStateSnapshot } from '@angular/router';
import { TitleStrategy } from '@angular/router';
import { TranslocoService } from '@jsverse/transloco';
import { switchMap } from 'rxjs';

/**
 * El `title` de cada ruta es una clave de traducción. El título de la pestaña
 * queda como «<página> · <app>» y se vuelve a traducir al cambiar de idioma.
 */
@Injectable({ providedIn: 'root' })
export class TituloTraducido extends TitleStrategy {
  private readonly titulo = inject(Title);
  private readonly transloco = inject(TranslocoService);
  private clave: string | undefined;

  constructor() {
    super();
    this.transloco.langChanges$
      .pipe(
        switchMap((idioma) => this.transloco.selectTranslation(idioma)),
        takeUntilDestroyed(),
      )
      .subscribe(() => this.poner());
  }

  override updateTitle(estado: RouterStateSnapshot): void {
    this.clave = this.buildTitle(estado);
    this.poner();
  }

  private poner(): void {
    const app = this.transloco.translate('app.nombre');
    const pagina = this.clave ? this.transloco.translate(this.clave) : '';
    this.titulo.setTitle(pagina ? `${pagina} · ${app}` : app);
  }
}
