import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { Shell } from './shell';

describe('Shell', () => {
  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [Shell, traduccionesDePrueba()],
      providers: [provideRouter([])],
    }).compileComponents();
  });

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
    await fixture.whenStable();
    const raiz: HTMLElement = fixture.nativeElement;
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
    await fixture.whenStable();
    const raiz: HTMLElement = fixture.nativeElement;

    expect(raiz.querySelector('nav')).toBeNull();
    expect(raiz.querySelector('at-selector-idioma')).not.toBeNull();
  });
});
