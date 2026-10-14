import { en, es } from '../../../testing/transloco';

function claves(objeto: object, prefijo = ''): string[] {
  return Object.entries(objeto)
    .flatMap(([clave, valor]) =>
      typeof valor === 'object' && valor !== null
        ? claves(valor, `${prefijo}${clave}.`)
        : [`${prefijo}${clave}`],
    )
    .sort();
}

function textos(objeto: object): unknown[] {
  return Object.values(objeto).flatMap((valor) =>
    typeof valor === 'object' && valor !== null ? textos(valor) : [valor],
  );
}

describe('Textos de la interfaz (public/i18n)', () => {
  it('es.json y en.json tienen las mismas claves', () => {
    expect(claves(en)).toEqual(claves(es));
  });

  it.each([
    ['es', es],
    ['en', en],
  ])('%s.json no tiene textos vacíos', (_idioma, traducciones) => {
    for (const texto of textos(traducciones)) {
      expect(typeof texto === 'string' && texto.trim().length > 0).toBe(true);
    }
  });
});
