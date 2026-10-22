import axe from 'axe-core';

/**
 * Problemas de accesibilidad que axe encuentra dentro de `raiz`, uno por
 * línea («regla: ayuda → selector»), para que la prueba diga qué arreglar.
 *
 * El contraste queda fuera: jsdom no pinta, así que axe no puede medirlo. Se
 * revisa en el navegador (ver el PR de la F-02).
 */
export async function problemasDeAccesibilidad(raiz: Element): Promise<string[]> {
  const resultado = await axe.run(raiz, {
    resultTypes: ['violations'],
    rules: { 'color-contrast': { enabled: false } },
  });
  return resultado.violations.flatMap((v) =>
    v.nodes.map((n) => `${v.id}: ${v.help} → ${n.target.join(' ')}`),
  );
}
