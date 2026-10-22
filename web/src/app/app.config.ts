import { provideHttpClient, withFetch } from '@angular/common/http';
import type { ApplicationConfig } from '@angular/core';
import {
  inject,
  isDevMode,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import {
  TitleStrategy,
  provideRouter,
  withComponentInputBinding,
  withInMemoryScrolling,
  withRouterConfig,
} from '@angular/router';
import { provideTransloco } from '@jsverse/transloco';
import { routes } from './app.routes';
import { CargadorTraducciones } from './core/i18n/cargador';
import { IDIOMAS, IDIOMA_POR_DEFECTO, IdiomaService } from './core/i18n/idioma';
import { TituloTraducido } from './core/i18n/titulo';

/** Opciones del router; las pruebas de rutas usan las mismas. */
export const opcionesRouter = [
  withComponentInputBinding(),
  // Las pantallas del aula reciben `:curso` y `:modulo` de sus rutas padre.
  withRouterConfig({ paramsInheritanceStrategy: 'always' }),
  withInMemoryScrolling({ scrollPositionRestoration: 'enabled' }),
] as const;

// Sin zone.js: desde Angular 21 la detección de cambios es zoneless por defecto.
export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideHttpClient(withFetch()),
    provideRouter(routes, ...opcionesRouter),
    { provide: TitleStrategy, useClass: TituloTraducido },
    provideTransloco({
      config: {
        availableLangs: [...IDIOMAS],
        defaultLang: IDIOMA_POR_DEFECTO,
        fallbackLang: IDIOMA_POR_DEFECTO,
        missingHandler: { useFallbackTranslation: true },
        reRenderOnLangChange: true,
        prodMode: !isDevMode(),
      },
      loader: CargadorTraducciones,
    }),
    provideAppInitializer(() => inject(IdiomaService).iniciar()),
  ],
};
