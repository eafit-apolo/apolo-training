import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { problemasDeAccesibilidad } from '../../../../testing/axe';
import { traduccionesDePrueba } from '../../../../testing/transloco';
import { cursoDe } from '../../../../testing/contenido';
import { armarCurso } from '../datos/armar';
import { BarraLateral } from './barra-lateral';

describe('BarraLateral', () => {
  async function crear(username: string, abierto: string, instructor = false) {
    await TestBed.configureTestingModule({
      imports: [BarraLateral, traduccionesDePrueba()],
      // El comodín recibe las navegaciones de los clics.
      providers: [provideRouter([{ path: '**', children: [] }])],
    }).compileComponents();
    const fixture = TestBed.createComponent(BarraLateral);
    fixture.componentRef.setInput('curso', armarCurso(cursoDe(username), instructor));
    fixture.componentRef.setInput('abierto', abierto);
    await fixture.whenStable();
    return fixture.nativeElement as HTMLElement;
  }

  function modulos(raiz: HTMLElement) {
    return Array.from(raiz.querySelectorAll<HTMLLIElement>('.modulos > li'));
  }

  it('los módulos bloqueados no son enlaces y dicen cuál hay que terminar', async () => {
    const raiz = await crear('ana', 'm05');
    const m06 = modulos(raiz)[6];
    expect(m06.querySelector('a')).toBeNull();
    expect(m06.textContent).toContain('6 · Núcleos y paralelismo');
    expect(m06.textContent).toContain('Termina el módulo 5 para abrirlo.');
  });

  it('los módulos abiertos enlazan a su página y muestran su avance', async () => {
    const raiz = await crear('ana', 'm05');
    const m01 = modulos(raiz)[1];
    expect(m01.querySelector('a')?.getAttribute('href')).toBe('/cursos/induccion/m01');
    expect(m01.textContent).toContain('2 de 2 lecciones');
    expect(m01.textContent).toContain('Completo');
  });

  it('despliega solo las lecciones del módulo abierto', async () => {
    const raiz = await crear('carla', 'm07');
    const lecciones = raiz.querySelectorAll('.lecciones a');
    expect(lecciones).toHaveLength(2);
    expect(lecciones[0].getAttribute('href')).toBe('/cursos/induccion/m07/vscode');
    expect(lecciones[0].textContent).toContain('(Completa)');
    expect(lecciones[1].textContent).toContain('(Pendiente)');
  });

  it('avisa al elegir un enlace (en celular el aula cierra el panel)', async () => {
    const raiz = await crear('ana', 'm05');
    const fixture = TestBed.createComponent(BarraLateral);
    fixture.componentRef.setInput('curso', armarCurso(cursoDe('bruno')));
    let avisos = 0;
    fixture.componentInstance.navego.subscribe(() => avisos++);
    await fixture.whenStable();
    (fixture.nativeElement as HTMLElement).querySelector<HTMLAnchorElement>('.curso a')?.click();
    expect(avisos).toBe(1);
    expect(raiz.querySelector('.curso a')?.getAttribute('href')).toBe('/cursos/induccion');
  });

  it('a un instructor le abre los bloqueados (para revisar el contenido)', async () => {
    const raiz = await crear('ana', 'm06', true);
    const m06 = modulos(raiz)[6];
    expect(m06.querySelector('a')?.getAttribute('href')).toBe('/cursos/induccion/m06');
    expect(m06.querySelectorAll('.lecciones a').length).toBeGreaterThan(0);
  });

  it('no tiene problemas de accesibilidad (axe)', async () => {
    const raiz = await crear('carla', 'm07');
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });
});
