/**
 * Clave de traducción en singular o plural: `plural('cursos.video', 2)` da
 * `cursos.video.otros`. Cada clave tiene `uno` y `otros` en es.json y en.json
 * (el español y el inglés solo distinguen 1 de los demás).
 */
export function plural(clave: string, n: number): string {
  return `${clave}.${n === 1 ? 'uno' : 'otros'}`;
}
