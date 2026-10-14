import type { TranslocoTestingOptions } from '@jsverse/transloco';
import { TranslocoTestingModule } from '@jsverse/transloco';
import en from '../../public/i18n/en.json';
import es from '../../public/i18n/es.json';

export { en, es };

/** Transloco con los textos reales de public/i18n, sin pasar por HTTP. */
export function traduccionesDePrueba(opciones: Partial<TranslocoTestingOptions> = {}) {
  return TranslocoTestingModule.forRoot({
    langs: { es, en },
    translocoConfig: {
      availableLangs: ['es', 'en'],
      defaultLang: 'es',
      fallbackLang: 'es',
      reRenderOnLangChange: true,
    },
    preloadLangs: true,
    ...opciones,
  });
}
