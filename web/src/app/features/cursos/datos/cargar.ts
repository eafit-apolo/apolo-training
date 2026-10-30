import { inject } from '@angular/core';
import type { CanActivateFn } from '@angular/router';
import { CatalogoService } from './catalogo';

/**
 * Las pantallas de cursos esperan a que llegue su contenido (B-04): así leen
 * de forma síncrona y los títulos de pestaña ya lo tienen. Siempre dejan
 * pasar: un curso que no existe muestra «no encontrada» y un error de red, su
 * aviso.
 */
export const cargarCatalogo: CanActivateFn = async () => {
  await inject(CatalogoService).cargarCatalogo();
  return true;
};

export const cargarCurso: CanActivateFn = async (ruta) => {
  await inject(CatalogoService).cargarCurso(ruta.paramMap.get('curso'));
  return true;
};
