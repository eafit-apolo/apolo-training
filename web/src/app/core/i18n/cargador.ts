import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import type { Translation, TranslocoLoader } from '@jsverse/transloco';

/** Textos de la interfaz desde public/i18n/<idioma>.json (ruta relativa a <base href>). */
@Injectable({ providedIn: 'root' })
export class CargadorTraducciones implements TranslocoLoader {
  private readonly http = inject(HttpClient);

  getTranslation(idioma: string) {
    return this.http.get<Translation>(`i18n/${idioma}.json`);
  }
}
