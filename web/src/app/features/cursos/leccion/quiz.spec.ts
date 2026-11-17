import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { problemasDeAccesibilidad } from '../../../../testing/axe';
import { ContenidoApiDePrueba, contenidoDePrueba } from '../../../../testing/contenido';
import { ANA, CARLA, botonCon, entrarComo } from '../../../../testing/sesion';
import { traduccionesDePrueba } from '../../../../testing/transloco';
import type { Simulacion } from '../../../../testing/video';
import { cargarVideo, pausarVideo, simularVideos } from '../../../../testing/video';
import { opcionesRouter } from '../../../app.config';
import { routes } from '../../../app.routes';
import { IdiomaService } from '../../../core/i18n/idioma';
import type { IntentoEntradaApi } from '../datos/api';
import { ContenidoApi } from '../datos/api';
import { CatalogoService } from '../datos/catalogo';
import { Quiz } from './quiz';

const TRABAJOS = '/cursos/induccion/m05/trabajos';

@Component({
  imports: [Quiz],
  template: `<at-quiz
    [quizId]="id()"
    [puedeEnviar]="true"
    [aprobado]="false"
    [faltaVideo]="false"
    [leccionCompleta]="false"
  />`,
})
class Anfitrion {
  readonly id = signal(0);
}

describe('Quiz de la lección (F-06)', () => {
  let api: ContenidoApiDePrueba;
  let harness: RouterTestingHarness;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [traduccionesDePrueba()],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(routes, ...opcionesRouter),
        contenidoDePrueba(),
      ],
    });
    api = TestBed.inject(ContenidoApiDePrueba);
    entrarComo(ANA);
  });

  async function listo(): Promise<HTMLElement> {
    for (let i = 0; i < 3; i++) {
      await new Promise((r) => setTimeout(r));
      await harness.fixture.whenStable();
    }
    harness.detectChanges();
    return harness.routeNativeElement as HTMLElement;
  }

  async function abrir(url: string): Promise<HTMLElement> {
    harness = await RouterTestingHarness.create(url);
    return listo();
  }

  const texto = (raiz: Element, selector: string) =>
    Array.from(raiz.querySelectorAll(selector)).map((e) =>
      e.textContent?.replace(/\s+/g, ' ').trim(),
    );
  const una = (raiz: Element, selector: string) =>
    raiz.querySelector(selector)?.textContent?.replace(/\s+/g, ' ').trim();

  const preguntas = (raiz: Element) =>
    Array.from(raiz.querySelectorAll<HTMLElement>('at-quiz .at-quiz-pregunta'));
  const opciones = (raiz: Element, pregunta: number) =>
    Array.from(preguntas(raiz)[pregunta].querySelectorAll<HTMLInputElement>('input'));

  /** Marca las opciones (la 0 es la primera) de una pregunta, como lo haría la persona. */
  function marcar(raiz: Element, pregunta: number, cuales: readonly number[]): void {
    for (const j of cuales) {
      opciones(raiz, pregunta)[j].click();
    }
  }

  /** `m05/trabajos`: la 1 es de una respuesta (correcta: la 2.ª) y la 2 de varias (correctas: 1.ª y 3.ª). */
  const responderBien = (raiz: Element) => {
    marcar(raiz, 0, [1]);
    marcar(raiz, 1, [0, 2]);
  };

  async function enviar(raiz: HTMLElement): Promise<HTMLElement> {
    botonCon(raiz, 'Enviar respuestas').click();
    return listo();
  }

  async function idDelQuiz(clave = 'm05/trabajos'): Promise<number> {
    const [modulo, leccion] = clave.split('/');
    const l = await api.leccion('induccion', modulo, leccion, 'es');
    return l?.quiz_id as number;
  }

  describe('se ve', () => {
    it('las preguntas con su número, el código en línea y la pista de cuántas se eligen', async () => {
      const raiz = await abrir(TRABAJOS);

      expect(texto(raiz, '.tarjeta h2')).toEqual(['Verifica tu práctica', 'Quiz']);
      expect(una(raiz, '.at-quiz-intro')).toBe(
        'Necesitas acertar el 80 % de las preguntas para aprobar. Puedes intentarlo las veces que quieras.',
      );
      expect(texto(raiz, '.at-quiz-numero')).toEqual(['Pregunta 1 de 2', 'Pregunta 2 de 2']);
      expect(texto(raiz, '.at-quiz-enunciado .at-md-html')).toEqual([
        'Pregunta 1: ¿qué hace squeue?',
        'Pregunta 2: ¿qué hace squeue?',
      ]);
      expect(raiz.querySelector('.at-quiz-enunciado code')?.textContent).toBe('squeue');
      expect(texto(raiz, '.at-quiz-pista')).toEqual([
        'Elige una respuesta.',
        'Marca todas las que apliquen.',
      ]);
      // Una respuesta: radios del mismo grupo; varias: casillas.
      expect(opciones(raiz, 0).map((i) => i.type)).toEqual(['radio', 'radio', 'radio']);
      expect(new Set(opciones(raiz, 0).map((i) => i.name)).size).toBe(1);
      expect(opciones(raiz, 1).map((i) => i.type)).toEqual([
        'checkbox',
        'checkbox',
        'checkbox',
        'checkbox',
      ]);
      expect(texto(raiz, '.at-quiz-pregunta:first-child .at-quiz-opcion')).toEqual([
        'Opción 1 de la pregunta 1',
        'Usar sbatch en la pregunta 1',
        'Opción 3 de la pregunta 1',
      ]);
      expect(raiz.querySelector('.at-quiz-opcion code')?.textContent).toBe('sbatch');
      expect(botonCon(raiz, 'Enviar respuestas')).toBeTruthy();
      expect(api.quizzes).toEqual(['m05/trabajos?lang=es']);
    });

    it('cada pregunta es un grupo con nombre accesible y sin errores de axe', async () => {
      const raiz = await abrir(TRABAJOS);

      const grupo = preguntas(raiz)[0];
      const nombre = raiz.querySelector(`#${grupo.getAttribute('aria-labelledby')}`);
      expect(nombre?.textContent).toContain('Pregunta 1 de 2');
      expect(nombre?.textContent).toContain('¿qué hace squeue?');
      expect(grupo.getAttribute('aria-describedby')).toContain('pista');
      expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
    });

    it('en inglés, con los mismos ids: lo marcado se conserva al cambiar el idioma', async () => {
      const raiz0 = await abrir(TRABAJOS);
      marcar(raiz0, 0, [1]);
      await TestBed.inject(IdiomaService).cambiar('en');
      const raiz = await listo();

      expect(texto(raiz, '.at-quiz-numero')).toEqual(['Question 1 of 2', 'Question 2 of 2']);
      expect(una(raiz, '.at-quiz-intro')).toContain('You need 80% of the questions right');
      expect(opciones(raiz, 0).map((i) => i.checked)).toEqual([false, true, false]);
      expect(api.quizzes).toEqual(['m05/trabajos?lang=es', 'm05/trabajos?lang=en']);
      expect(raiz.querySelector('.at-quiz-aviso')).toBeNull();
    });

    it('un quiz sin traducir sale en español, con aviso y lang="es"', async () => {
      api.quizSinIngles.add('m05/trabajos');
      await TestBed.inject(IdiomaService).cambiar('en');
      const raiz = await abrir(TRABAJOS);

      expect(una(raiz, '.at-quiz-aviso')).toBe(
        "This quiz isn't translated yet: you see it in Spanish.",
      );
      expect(raiz.querySelector('.at-quiz-enunciado')?.getAttribute('lang')).toBe('es');
      expect(raiz.querySelector('.at-quiz-opcion-texto')?.getAttribute('lang')).toBe('es');
      expect(una(raiz, '.at-quiz-numero')).toBe('Question 1 of 2');
    });

    it('lo que viene del quiz es texto: ni HTML ni enlaces peligrosos', async () => {
      const quiz = await api.quiz(await idDelQuiz(), 'es');
      vi.spyOn(api, 'quiz').mockResolvedValue({
        ...quiz,
        preguntas: quiz.preguntas.map((p, i) => ({
          ...p,
          enunciado: i === 0 ? '<img src=x onerror="window.pwned=1"> **negrita**' : p.enunciado,
          opciones: p.opciones.map((o, j) => ({
            ...o,
            texto: i === 0 && j === 0 ? '<b>HTML</b> [enlace](javascript:alert(1))' : o.texto,
          })),
        })),
      });
      const raiz = await abrir(TRABAJOS);

      const quizEnPantalla = raiz.querySelector('at-quiz') as HTMLElement;
      expect(quizEnPantalla.querySelector('img')).toBeNull();
      expect(quizEnPantalla.textContent).toContain('<img src=x onerror="window.pwned=1">');
      expect(quizEnPantalla.querySelector('.at-quiz-enunciado strong')?.textContent).toBe(
        'negrita',
      );
      expect(quizEnPantalla.querySelector('.at-quiz-opcion b')).toBeNull();
      expect(quizEnPantalla.querySelector('.at-quiz-opcion a')).toBeNull();
      expect(texto(raiz, '.at-quiz-opcion-texto')[0]).toBe('<b>HTML</b> enlace');
      expect((window as { pwned?: number }).pwned).toBeUndefined();
    });
  });

  describe('enviar y calificar', () => {
    it('con preguntas sin contestar no envía, dice cuáles y lleva el foco a la primera', async () => {
      const raiz = await abrir(TRABAJOS);

      const final = await enviar(raiz);

      expect(api.intentos).toEqual([]);
      expect(una(final, '.at-quiz-acciones [role="alert"]')).toBe(
        'Responde todas las preguntas antes de enviar.',
      );
      expect(texto(final, '.at-quiz-falta')).toEqual([
        'Elige una respuesta para esta pregunta.',
        'Elige una respuesta para esta pregunta.',
      ]);
      expect(document.activeElement).toBe(opciones(final, 0)[0]);
      const grupo = preguntas(final)[0];
      expect(grupo.getAttribute('aria-describedby')).toContain('falta');
      expect(await problemasDeAccesibilidad(final)).toEqual([]);

      // Al contestar una, se le quita su aviso; el general sigue hasta que no falte ninguna.
      marcar(final, 0, [0]);
      let ahora = await listo();
      expect(ahora.querySelectorAll('.at-quiz-falta')).toHaveLength(1);
      expect(ahora.querySelector('.at-quiz-acciones [role="alert"]')).not.toBeNull();
      marcar(ahora, 1, [3]);
      ahora = await listo();
      expect(ahora.querySelector('.at-quiz-falta')).toBeNull();
      expect(ahora.querySelector('.at-quiz-acciones [role="alert"]')).toBeNull();
    });

    it('todas bien: manda una opción por pregunta de una respuesta y todas las marcadas, aprueba y completa la lección', async () => {
      const recargar = vi.spyOn(TestBed.inject(CatalogoService), 'recargar');
      const raiz = await abrir(TRABAJOS);
      responderBien(raiz);

      const final = await enviar(raiz);

      const correctas = api.correctasDe(await idDelQuiz());
      const entrada = api.intentos[0].entrada as IntentoEntradaApi;
      expect(entrada.respuestas).toHaveLength(2);
      for (const r of entrada.respuestas) {
        expect(new Set(r.opciones)).toEqual(correctas.get(r.pregunta_id));
      }
      expect(entrada.respuestas.map((r) => r.opciones.length)).toEqual([1, 2]);

      const resumen = final.querySelector<HTMLElement>('.at-quiz-resumen');
      expect(texto(final, '.at-quiz-resumen p')).toEqual([
        '¡Aprobaste! Acertaste 2 de 2 (100 %).',
        'La lección está completa.',
        'Tu mejor puntaje: 100 %.',
      ]);
      expect(resumen?.getAttribute('role')).toBe('status');
      expect(document.activeElement).toBe(resumen);
      expect(texto(final, '.at-quiz-estado-pregunta')).toEqual(['Correcta', 'Correcta']);
      expect(texto(final, '.at-quiz-explicacion')).toEqual([
        'Explicación de la pregunta 1, con sacct.',
        'Explicación de la pregunta 2, con sacct.',
      ]);
      expect(final.querySelector('.at-quiz-explicacion code')?.textContent).toBe('sacct');
      // La lección quedó completa y el catálogo se puso al día.
      expect(una(final, '.completar .hecha')).toBe('Completaste esta lección');
      expect(final.querySelector('.meta')?.textContent).toContain('Completa');
      expect(recargar).toHaveBeenCalledTimes(1);
      expect(await problemasDeAccesibilidad(final)).toEqual([]);
    });

    it('con una mal no aprueba: dice cuáles, sin la opción correcta, y la lección sigue pendiente', async () => {
      const recargar = vi.spyOn(TestBed.inject(CatalogoService), 'recargar');
      const raiz = await abrir(TRABAJOS);
      marcar(raiz, 0, [0]); // la correcta es la 2.ª
      marcar(raiz, 1, [0, 2]);

      const final = await enviar(raiz);

      expect(texto(final, '.at-quiz-resumen p')).toEqual([
        'No aprobaste esta vez. Acertaste 1 de 2 (50 %) y necesitas 80 %.',
        'Lee la explicación de cada pregunta e inténtalo de nuevo.',
        'Tu mejor puntaje: 50 %.',
      ]);
      expect(final.querySelector('.at-quiz-resumen.aprobado')).toBeNull();
      expect(texto(final, '.at-quiz-estado-pregunta')).toEqual(['Incorrecta', 'Correcta']);
      expect(
        preguntas(final).map((p) => [
          p.classList.contains('incorrecta'),
          p.classList.contains('correcta'),
        ]),
      ).toEqual([
        [true, false],
        [false, true],
      ]);
      expect(texto(final, '.at-quiz-explicacion')).toHaveLength(2);
      expect(preguntas(final)[0].getAttribute('aria-describedby')).toContain('veredicto');
      // Con el resultado a la vista, las respuestas no se cambian.
      expect(
        Array.from(final.querySelectorAll<HTMLInputElement>('at-quiz input')).every(
          (i) => i.disabled,
        ),
      ).toBe(true);
      expect(texto(final, '.at-quiz-acciones button')).toEqual(['Intentar de nuevo']);
      expect(una(final, '.completar')).toBe('Esta lección se completa al aprobar el quiz.');
      expect(final.querySelector('.completar button')).toBeNull();
      expect(recargar).not.toHaveBeenCalled();
      expect(await problemasDeAccesibilidad(final)).toEqual([]);
    });

    it('sin puntos parciales: una pregunta de varias respuestas con solo una de las correctas es incorrecta', async () => {
      const raiz = await abrir(TRABAJOS);
      marcar(raiz, 0, [1]);
      marcar(raiz, 1, [0]); // falta la 3.ª

      const final = await enviar(raiz);

      expect(texto(final, '.at-quiz-estado-pregunta')).toEqual(['Correcta', 'Incorrecta']);
      expect(una(final, '.at-quiz-veredicto')).toContain('Acertaste 1 de 2 (50 %)');
    });

    it('«Intentar de nuevo» reabre las preguntas con lo marcado y el foco en la primera', async () => {
      const raiz = await abrir(TRABAJOS);
      marcar(raiz, 0, [0]);
      marcar(raiz, 1, [0, 2]);
      await enviar(raiz);

      botonCon(raiz, 'Intentar de nuevo').click();
      const final = await listo();

      expect(final.querySelector('.at-quiz-resumen')).toBeNull();
      expect(final.querySelector('.at-quiz-estado-pregunta')).toBeNull();
      expect(opciones(final, 0).map((i) => i.checked)).toEqual([true, false, false]);
      expect(opciones(final, 1).map((i) => i.checked)).toEqual([true, false, true, false]);
      expect(opciones(final, 0).every((i) => !i.disabled)).toBe(true);
      expect(document.activeElement).toBe(opciones(final, 0)[0]);
      expect(botonCon(final, 'Enviar respuestas')).toBeTruthy();

      // En una pregunta de una respuesta, elegir otra opción cambia la elegida.
      marcar(final, 0, [1]);
      expect((await listo(), opciones(final, 0).map((i) => i.checked))).toEqual([
        false,
        true,
        false,
      ]);
      const aprobado = await enviar(final);
      expect(una(aprobado, '.at-quiz-veredicto')).toContain('¡Aprobaste!');
      expect(api.intentos).toHaveLength(2);
    });

    it('en una pregunta de varias respuestas, desmarcar quita la opción', async () => {
      const raiz = await abrir(TRABAJOS);
      marcar(raiz, 0, [1]);
      marcar(raiz, 1, [0, 2, 2]); // marca la 1.ª y la 3.ª, y desmarca la 3.ª

      await enviar(raiz);

      expect(api.intentos[0].entrada.respuestas[1].opciones).toHaveLength(1);
    });

    it('el mejor puntaje no baja y la lección no se descompleta', async () => {
      const raiz = await abrir(TRABAJOS);
      responderBien(raiz);
      await enviar(raiz);
      botonCon(raiz, 'Intentar de nuevo').click();
      await listo();
      marcar(raiz, 0, [0]); // la 2 sigue marcada y bien

      const final = await enviar(raiz);

      expect(texto(final, '.at-quiz-resumen p')).toEqual([
        'No aprobaste esta vez. Acertaste 1 de 2 (50 %) y necesitas 80 %.',
        'Lee la explicación de cada pregunta e inténtalo de nuevo.',
        'Tu mejor puntaje: 100 %.',
      ]);
      expect(una(final, '.completar .hecha')).toBe('Completaste esta lección');
    });

    it('al abrir de nuevo el quiz muestra el mejor puntaje de antes', async () => {
      const raiz = await abrir(TRABAJOS);
      marcar(raiz, 0, [0]);
      marcar(raiz, 1, [0, 2]);
      await enviar(raiz);

      const router = TestBed.inject(Router);
      await router.navigateByUrl('/cursos/induccion');
      await listo();
      await router.navigateByUrl(TRABAJOS);
      const otra = await listo();

      expect(una(otra, '.at-quiz-intro')).toContain('Tu mejor puntaje: 50 %.');
      expect(una(otra, '.at-quiz-intro')).toContain('Necesitas acertar el 80 %');
    });

    it('un quiz ya aprobado lo dice y deja volver a intentar', async () => {
      const raiz = await abrir('/cursos/induccion/m04/modulos');

      expect(una(raiz, '.at-quiz-intro')).toBe(
        'Ya aprobaste este quiz. Puedes volver a intentarlo si quieres mejorar tu puntaje.',
      );
      expect(opciones(raiz, 0).every((i) => !i.disabled)).toBe(true);
      expect(botonCon(raiz, 'Enviar respuestas')).toBeTruthy();
    });

    it('otra lección con quiz empieza sin respuestas ni resultado', async () => {
      const raiz = await abrir(TRABAJOS);
      responderBien(raiz);
      await enviar(raiz);

      await TestBed.inject(Router).navigateByUrl('/cursos/induccion/m04/modulos');
      const otra = await listo();

      expect(otra.querySelector('.at-quiz-resumen')).toBeNull();
      expect(opciones(otra, 0).some((i) => i.checked)).toBe(false);
      expect(opciones(otra, 1).some((i) => i.checked)).toBe(false);
    });
  });

  describe('el componente suelto', () => {
    it('al cambiar de quiz olvida lo marcado y el resultado del anterior', async () => {
      const fixture = TestBed.createComponent(Anfitrion);
      const raiz = fixture.nativeElement as HTMLElement;
      const esperar = async () => {
        for (let i = 0; i < 3; i++) {
          await new Promise((r) => setTimeout(r));
          await fixture.whenStable();
        }
        fixture.detectChanges();
      };
      fixture.componentInstance.id.set(await idDelQuiz('m05/trabajos'));
      await esperar();
      responderBien(raiz);
      botonCon(raiz, 'Enviar respuestas').click();
      await esperar();
      expect(raiz.querySelector('.at-quiz-resumen')).not.toBeNull();

      fixture.componentInstance.id.set(await idDelQuiz('m04/modulos'));
      await esperar();

      expect(raiz.querySelector('.at-quiz-resumen')).toBeNull();
      expect(raiz.querySelectorAll('.at-quiz-pregunta').length).toBeGreaterThan(0);
      expect(
        Array.from(raiz.querySelectorAll<HTMLInputElement>('input')).some(
          (i) => i.checked || i.disabled,
        ),
      ).toBe(false);
      expect(api.intentos).toHaveLength(1);
    });
  });

  describe('con el video y «Marcar como completada»', () => {
    let simulacion: Simulacion;

    beforeEach(() => {
      simulacion = simularVideos();
    });

    afterEach(() => simulacion.restaurar());

    it('una lección con quiz no tiene botón: se completa al aprobarlo', async () => {
      const raiz = await abrir(TRABAJOS);

      expect(raiz.querySelector('.completar button')).toBeNull();
      expect(una(raiz, '.completar')).toBe('Esta lección se completa al aprobar el quiz.');
    });

    it('con un video subido y un quiz, dice que faltan los dos', async () => {
      api.conVideo.add('m05/trabajos');
      const raiz = await abrir(TRABAJOS);

      expect(raiz.querySelector('.completar button')).toBeNull();
      expect(una(raiz, '.completar')).toBe(
        'Esta lección se completa al ver el 90 % del video y aprobar el quiz.',
      );
    });

    it('si aprueba antes de ver el video, no se completa y dice lo que falta', async () => {
      api.conVideo.add('m05/trabajos');
      const recargar = vi.spyOn(TestBed.inject(CatalogoService), 'recargar');
      const raiz = await abrir(TRABAJOS);
      responderBien(raiz);

      const final = await enviar(raiz);

      expect(texto(final, '.at-quiz-resumen p')).toEqual([
        '¡Aprobaste! Acertaste 2 de 2 (100 %).',
        'Para completar la lección falta ver el 90 % del video.',
        'Tu mejor puntaje: 100 %.',
      ]);
      expect(una(final, '.completar')).toBe(
        'Aprobaste el quiz. Falta ver el 90 % del video para completar esta lección.',
      );
      expect(final.querySelector('.completar .hecha')).toBeNull();
      expect(final.querySelector('.meta')?.textContent).toContain('Pendiente');
      expect(recargar).not.toHaveBeenCalled();
    });

    it('al ver el 90 % del video con el quiz pendiente, no se completa y lo anuncia', async () => {
      api.conVideo.add('m05/trabajos');
      const recargar = vi.spyOn(TestBed.inject(CatalogoService), 'recargar');
      const raiz = await abrir(TRABAJOS);
      const video = raiz.querySelector('video') as HTMLVideoElement;
      const estado = simulacion.de(video);
      cargarVideo(video);

      estado.tiempo = 280;
      pausarVideo(estado, video);
      const final = await listo();

      expect(una(final, '.anuncio')).toBe(
        'Viste el video. Falta aprobar el quiz para completar esta lección.',
      );
      expect(una(final, '.completar')).toBe(
        'Viste el video. Falta aprobar el quiz para completar esta lección.',
      );
      expect(final.querySelector('.completar .hecha')).toBeNull();
      expect(final.querySelector('.meta')?.textContent).toContain('Pendiente');
      expect(recargar).not.toHaveBeenCalled();
    });

    it('si ya vio el video, falta solo el quiz, y al aprobarlo se completa', async () => {
      api.conVideo.add('m05/trabajos');
      const leccion = await api.leccion('induccion', 'm05', 'trabajos', 'es');
      await api.reportarVideo({
        leccion_id: leccion?.id as number,
        video_id: leccion?.videos[0].video.id as number,
        segundo: 280,
      });
      const recargar = vi.spyOn(TestBed.inject(CatalogoService), 'recargar');
      const raiz = await abrir(TRABAJOS);

      expect(una(raiz, '.completar')).toBe(
        'Viste el video. Falta aprobar el quiz para completar esta lección.',
      );
      responderBien(raiz);
      const final = await enviar(raiz);

      expect(una(final, '.at-quiz-resumen')).toContain('La lección está completa.');
      expect(una(final, '.completar .hecha')).toBe('Completaste esta lección');
      expect(recargar).toHaveBeenCalledTimes(1);
    });

    it('una lección con video y sin quiz sigue igual: se completa al verlo', async () => {
      api.sinQuiz.add('m05/trabajos');
      api.conVideo.add('m05/trabajos');
      const raiz = await abrir(TRABAJOS);

      expect(raiz.querySelector('at-quiz')).toBeNull();
      expect(una(raiz, '.completar')).toBe('Esta lección se completa al ver el 90 % del video.');
    });
  });

  describe('permisos y errores', () => {
    it('una instructora en un módulo bloqueado lee el quiz, pero no lo puede enviar', async () => {
      entrarComo(CARLA);
      const raiz = await abrir('/cursos/induccion/m08/cierre');

      expect(preguntas(raiz)).toHaveLength(8);
      expect(una(raiz, '.at-quiz-intro')).toBe(
        'Puedes leer este quiz, pero no enviarlo: el módulo todavía está bloqueado para los estudiantes.',
      );
      expect(
        Array.from(raiz.querySelectorAll<HTMLInputElement>('at-quiz input')).every(
          (i) => i.disabled,
        ),
      ).toBe(true);
      expect(texto(raiz, 'at-quiz button')).toEqual([]);
    });

    it('si no puede calificar, lo dice y deja lo marcado para reintentar', async () => {
      const raiz = await abrir(TRABAJOS);
      responderBien(raiz);
      vi.spyOn(api, 'enviarIntento').mockRejectedValueOnce(
        new HttpErrorResponse({ status: 500, error: { codigo: 'error_interno' } }),
      );

      const final = await enviar(raiz);

      expect(una(final, '.at-quiz-error')).toBe(
        'No pudimos calificar tu quiz. Inténtalo de nuevo.',
      );
      expect(final.querySelector('.at-quiz-resumen')).toBeNull();
      expect(opciones(final, 1).map((i) => i.checked)).toEqual([true, false, true, false]);
      expect(opciones(final, 0).every((i) => !i.disabled)).toBe(true);

      const reintento = await enviar(final);
      expect(una(reintento, '.at-quiz-veredicto')).toContain('¡Aprobaste!');
    });

    it('si la API dice que el módulo está bloqueado, lo avisa y pone al día el catálogo', async () => {
      const recargar = vi.spyOn(TestBed.inject(CatalogoService), 'recargar');
      const raiz = await abrir(TRABAJOS);
      responderBien(raiz);
      vi.spyOn(api, 'enviarIntento').mockRejectedValueOnce(
        new HttpErrorResponse({ status: 403, error: { codigo: 'modulo_bloqueado' } }),
      );

      const final = await enviar(raiz);

      expect(una(final, '.at-quiz-error')).toBe(
        'Este módulo todavía está bloqueado: termina el anterior para contestar el quiz.',
      );
      expect(recargar).toHaveBeenCalled();
    });

    it('si el quiz no carga, lo dice y deja reintentar', async () => {
      vi.spyOn(api, 'quiz').mockRejectedValueOnce(
        new HttpErrorResponse({ status: 500, error: { codigo: 'error_interno' } }),
      );
      const raiz = await abrir(TRABAJOS);

      expect(una(raiz, '.at-quiz-estado [role="alert"], at-quiz [role="alert"]')).toContain(
        'No pudimos cargar el quiz',
      );
      expect(raiz.querySelector('at-quiz .at-quiz-pregunta')).toBeNull();
      // El resto de la lección sigue a la vista.
      expect(raiz.querySelector('.texto-leccion h2')?.textContent).toBe('Objetivos');

      const reintentar = Array.from(raiz.querySelectorAll<HTMLElement>('at-quiz button')).find(
        (b) => b.textContent?.trim() === 'Reintentar',
      );
      reintentar?.click();
      const final = await listo();

      expect(preguntas(final)).toHaveLength(2);
    });

    it('si el quiz dice que el módulo está bloqueado al cargar, pone al día el catálogo', async () => {
      const recargar = vi.spyOn(TestBed.inject(CatalogoService), 'recargar');
      vi.spyOn(api, 'quiz').mockRejectedValue(
        new HttpErrorResponse({ status: 403, error: { codigo: 'modulo_bloqueado' } }),
      );

      await abrir(TRABAJOS);

      expect(recargar).toHaveBeenCalled();
    });
  });
});

describe('ContenidoApi: quiz (B-06)', () => {
  let api: ContenidoApi;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(ContenidoApi);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('pide el quiz por su id, en el idioma de la interfaz', async () => {
    const carga = api.quiz(7, 'en');
    const peticion = http.expectOne((r) => r.url === '/api/quizzes/7');
    expect(peticion.request.method).toBe('GET');
    expect(peticion.request.params.get('lang')).toBe('en');
    peticion.flush({ id: 7, preguntas: [] });

    expect((await carga).id).toBe(7);
  });

  it('envía las respuestas con POST y recibe el resultado', async () => {
    const entrada = { respuestas: [{ pregunta_id: 3, opciones: [11, 12] }] };
    const envio = api.enviarIntento(7, entrada, 'es');
    const peticion = http.expectOne((r) => r.url === '/api/quizzes/7/intentos');
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.params.get('lang')).toBe('es');
    expect(peticion.request.body).toEqual(entrada);
    peticion.flush({ id: 1, puntaje: 100, aprobado: true }, { status: 201, statusText: 'Created' });

    expect((await envio).aprobado).toBe(true);
  });
});
