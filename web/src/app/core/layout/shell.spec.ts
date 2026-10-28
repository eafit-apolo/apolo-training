import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import type { ComponentFixture } from '@angular/core/testing';
import { DeferBlockState, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { problemasDeAccesibilidad } from '../../../testing/axe';
import { ANA, CARLA, DIEGO, entrarComo } from '../../../testing/sesion';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { Shell } from './shell';

describe('Shell', () => {
  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [Shell, traduccionesDePrueba()],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    entrarComo(ANA);
  });

  /** El selector de idioma y los menús van con @defer (on idle): se pintan aquí. */
  async function conDiferidos(fixture: ComponentFixture<Shell>): Promise<HTMLElement> {
    await fixture.whenStable();
    for (const bloque of await fixture.getDeferBlocks()) {
      await bloque.render(DeferBlockState.Complete);
    }
    return fixture.nativeElement;
  }

  function boton(raiz: HTMLElement, texto: string): HTMLButtonElement {
    const botones = Array.from(
      raiz.querySelectorAll<HTMLButtonElement>('mat-button-toggle button'),
    );
    const encontrado = botones.find((b) => b.textContent?.trim() === texto);
    if (!encontrado) {
      throw new Error(`No hay botón «${texto}»`);
    }
    return encontrado;
  }

  // DoD 2 de la F-01.
  it('cambia los textos al elegir otro idioma, sin recargar', async () => {
    const fixture = TestBed.createComponent(Shell);
    const raiz = await conDiferidos(fixture);
    expect(raiz.querySelector('nav')?.textContent).toContain('Mi progreso');

    boton(raiz, 'EN').click();
    await fixture.whenStable();

    expect(raiz.querySelector('nav')?.textContent).toContain('My progress');
    expect(raiz.querySelector('.marca')?.textContent).toContain('Induction course');
    expect(document.documentElement.lang).toBe('en');

    boton(raiz, 'ES').click();
    await fixture.whenStable();

    expect(raiz.querySelector('nav')?.textContent).toContain('Mi progreso');
  });

  it('las pantallas de cuenta no muestran el menú, pero sí el idioma', async () => {
    const fixture = TestBed.createComponent(Shell);
    fixture.componentRef.setInput('sinMenu', true);
    const raiz = await conDiferidos(fixture);

    expect(raiz.querySelector('nav')).toBeNull();
    expect(raiz.querySelector('at-menu-usuario')).toBeNull();
    expect(raiz.querySelector('at-selector-idioma')).not.toBeNull();
  });

  function enlacesDelMenu(raiz: HTMLElement): string[] {
    return Array.from(raiz.querySelectorAll('nav a')).map((a) => a.textContent?.trim() ?? '');
  }

  it('Panel y Administración solo se muestran a su rol', async () => {
    const fixture = TestBed.createComponent(Shell);
    await fixture.whenStable();
    const raiz: HTMLElement = fixture.nativeElement;
    expect(enlacesDelMenu(raiz)).toEqual(['Cursos', 'Mi progreso']);

    entrarComo(CARLA);
    await fixture.whenStable();
    expect(enlacesDelMenu(raiz)).toEqual(['Cursos', 'Mi progreso', 'Panel']);

    entrarComo(DIEGO);
    await fixture.whenStable();
    expect(enlacesDelMenu(raiz)).toEqual(['Cursos', 'Mi progreso', 'Panel', 'Administración']);
  });

  it('el menú de usuario muestra el nombre y el perfil del clúster', async () => {
    const fixture = TestBed.createComponent(Shell);
    const raiz = await conDiferidos(fixture);

    const boton = raiz.querySelector('at-menu-usuario button');
    expect(boton?.textContent).toContain('Ana · Apolo II');
    expect(boton?.getAttribute('aria-haspopup')).toBe('menu');
    expect(raiz.querySelector('at-menu-movil button')?.getAttribute('aria-label')).toBe(
      'Menú principal',
    );
    expect(raiz.textContent).not.toContain('Probar como');
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });

  it('sin sesión no hay menú de usuario', async () => {
    entrarComo(null);
    const fixture = TestBed.createComponent(Shell);
    const raiz = await conDiferidos(fixture);
    expect(raiz.querySelector('at-menu-usuario button')).toBeNull();
  });
});
