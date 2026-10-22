import { inject } from '@angular/core';
import type { ActivatedRouteSnapshot, ResolveFn } from '@angular/router';
import { tituloLiteral } from '../../../core/i18n/titulo';
import { CatalogoService } from './catalogo';

const NO_ENCONTRADA = 'paginas.noEncontrada';

// Los parámetros de las rutas padre llegan porque la app usa
// `paramsInheritanceStrategy: 'always'` (app.config.ts).
function parametro(ruta: ActivatedRouteSnapshot, nombre: string): string | undefined {
  return ruta.paramMap.get(nombre) ?? undefined;
}

/** Título de la pestaña: el nombre del curso, del módulo o de la lección. */
export const tituloCurso: ResolveFn<string> = (ruta) => {
  const curso = inject(CatalogoService).curso(parametro(ruta, 'curso'));
  return curso ? tituloLiteral(curso.titulo) : NO_ENCONTRADA;
};

export const tituloModulo: ResolveFn<string> = (ruta) => {
  const catalogo = inject(CatalogoService);
  const modulo = catalogo.modulo(
    catalogo.curso(parametro(ruta, 'curso')),
    parametro(ruta, 'modulo'),
  );
  return modulo ? tituloLiteral(`${modulo.numero} · ${modulo.titulo}`) : NO_ENCONTRADA;
};

export const tituloLeccion: ResolveFn<string> = (ruta) => {
  const catalogo = inject(CatalogoService);
  const modulo = catalogo.modulo(
    catalogo.curso(parametro(ruta, 'curso')),
    parametro(ruta, 'modulo'),
  );
  const leccion = catalogo.leccion(modulo, parametro(ruta, 'leccion'));
  return leccion ? tituloLiteral(`${leccion.numero} · ${leccion.titulo}`) : NO_ENCONTRADA;
};
