import { cursoDe, cursoDeEjemplo } from '../../../../testing/contenido';
import { armarCurso } from './armar';

/** Lo que la web arma con la respuesta de la API para un usuario de ejemplo. */
function cursoPara(username: string, puedeVerBloqueados = false) {
  return armarCurso(cursoDe(username), puedeVerBloqueados);
}

describe('armarCurso (respuesta de la API → pantallas)', () => {
  it('trae los 9 módulos con sus slugs, 82 min y 24 preguntas', () => {
    const curso = cursoPara('bruno');
    expect(curso.modulos.map((m) => m.id)).toEqual([
      'm00',
      'm01',
      'm02',
      'm03',
      'm04',
      'm05',
      'm06',
      'm07',
      'm08',
    ]);
    expect(curso.duracion).toBe(82);
    expect(curso.modulos.reduce((n, m) => n + m.preguntas, 0)).toBe(24);
  });

  it('sin avance: el módulo 0 en curso, los demás bloqueados y «Empezar»', () => {
    const curso = cursoPara('bruno');
    expect(curso.modulos.map((m) => m.estado)).toEqual(['en-curso', ...Array(8).fill('bloqueado')]);
    expect(curso.continuar?.id).toBe('m00/bienvenida');
    expect(curso.empezado).toBe(false);
    expect(curso.avance).toBe(0);
  });

  it('a mitad del curso: numera las lecciones y apunta a la siguiente', () => {
    const curso = cursoPara('ana');
    expect(curso.modulos.map((m) => m.estado)).toEqual([
      ...Array(5).fill('completo'),
      'en-curso',
      ...Array(3).fill('bloqueado'),
    ]);
    expect(curso.modulosCompletos).toBe(5);
    expect(curso.continuar?.id).toBe('m05/trabajos');
    expect(curso.continuar?.numero).toBe('5.1');
    expect(curso.empezado).toBe(true);
    expect(curso.avance).toBe(55);
  });

  it('cuenta las lecciones hechas de un módulo a medias', () => {
    const m07 = cursoPara('carla').modulos[7];
    expect(m07.estado).toBe('en-curso');
    expect(m07.hechas).toBe(1);
    expect(m07.lecciones.map((l) => l.completa)).toEqual([true, false]);
  });

  it('curso terminado: nada para continuar', () => {
    const curso = cursoPara('diego');
    expect(curso.modulos.every((m) => m.estado === 'completo')).toBe(true);
    expect(curso.continuar).toBeNull();
    expect(curso.avance).toBe(100);
  });

  it('un estudiante no abre los bloqueados; instructores y admins sí', () => {
    expect(cursoPara('ana').modulos.map((m) => m.abierto)).toEqual([
      ...Array(6).fill(true),
      ...Array(3).fill(false),
    ]);
    const paraInstructor = cursoPara('ana', true);
    expect(paraInstructor.modulos.every((m) => m.abierto)).toBe(true);
    expect(paraInstructor.modulos[6].estado).toBe('bloqueado');
  });

  it('sin descripción, texto vacío', () => {
    const api = { ...cursoDeEjemplo([]), descripcion: null };
    expect(armarCurso(api).descripcion).toBe('');
  });
});
