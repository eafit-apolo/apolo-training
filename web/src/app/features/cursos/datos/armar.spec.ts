import { armarCurso, idModulo } from './armar';
import { CURSOS_EJEMPLO, PROGRESO_EJEMPLO } from './datos-ejemplo';

const CONTENIDO = CURSOS_EJEMPLO[0];

function cursoDe(username: string) {
  return armarCurso(CONTENIDO, new Set(PROGRESO_EJEMPLO[username]));
}

describe('armarCurso', () => {
  it('suma lo del mapa: 9 módulos, 82 min y 24 preguntas', () => {
    const curso = cursoDe('bruno');
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

  it('sin avance: el módulo 0 en curso y los demás bloqueados', () => {
    const curso = cursoDe('bruno');
    expect(curso.modulos.map((m) => m.estado)).toEqual(['en-curso', ...Array(8).fill('bloqueado')]);
    expect(curso.continuar?.id).toBe('m00/bienvenida');
    expect(curso.empezado).toBe(false);
    expect(curso.avance).toBe(0);
  });

  it('a mitad del curso: completos hasta el 4, el 5 en curso y desde el 6 bloqueados', () => {
    const curso = cursoDe('ana');
    expect(curso.modulos.map((m) => m.estado)).toEqual([
      ...Array(5).fill('completo'),
      'en-curso',
      ...Array(3).fill('bloqueado'),
    ]);
    expect(curso.modulosCompletos).toBe(5);
    expect(curso.continuar?.id).toBe('m05/trabajos');
    expect(curso.continuar?.numero).toBe('5.1');
    // 6 de 11 lecciones.
    expect(curso.avance).toBe(55);
  });

  it('cuenta las lecciones hechas de un módulo a medias', () => {
    const m07 = cursoDe('carla').modulos[7];
    expect(m07.estado).toBe('en-curso');
    expect(m07.hechas).toBe(1);
    expect(m07.lecciones.map((l) => l.completa)).toEqual([true, false]);
    expect(cursoDe('carla').continuar?.id).toBe('m07/graduacion');
  });

  it('curso terminado: todo completo y nada para continuar', () => {
    const curso = cursoDe('diego');
    expect(curso.modulos.every((m) => m.estado === 'completo')).toBe(true);
    expect(curso.continuar).toBeNull();
    expect(curso.avance).toBe(100);
  });

  it('una lección marcada en un módulo bloqueado no cuenta ni lo abre', () => {
    const curso = armarCurso(CONTENIDO, new Set(['m06/paralelismo']));
    expect(curso.modulos[6].estado).toBe('bloqueado');
    expect(curso.modulos[6].hechas).toBe(0);
  });

  it('idModulo rellena con ceros como content/es/', () => {
    expect(idModulo(5)).toBe('m05');
    expect(idModulo(12)).toBe('m12');
  });
});
