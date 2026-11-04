import { MUESTRA_ES } from '../../../../testing/leccion-muestra';
import type { Bloque, BloqueCodigo, BloqueHtml, BloqueLista, BloquePestanas } from './markdown';
import { analizarMarkdown, bloqueDeCodigo, urlSegura } from './markdown';

function deTipo<T extends Bloque['tipo']>(bloques: readonly Bloque[], tipo: T) {
  return bloques.filter((b): b is Extract<Bloque, { tipo: T }> => b.tipo === tipo);
}

function html(bloques: readonly Bloque[]): string {
  return deTipo(bloques, 'html')
    .map((b: BloqueHtml) => b.html)
    .join('');
}

describe('analizarMarkdown (F-04)', () => {
  it('parte la lección de muestra en texto, código y pestañas', () => {
    const bloques = analizarMarkdown(MUESTRA_ES);

    expect(bloques.map((b) => b.tipo)).toEqual([
      'html', // Objetivos y el inicio del resumen
      'codigo', // el script
      'html',
      'codigo', // sbatch, squeue, sacct
      'codigo', // la salida de squeue
      'html', // la tabla
      'pestanas',
      'html', // ## Práctica
      'lista', // pasos con código
      'html', // ## Si algo falla
    ]);
    expect(html(bloques)).toContain('<h2>Objetivos</h2>');
  });

  it('las pestañas seguidas forman un grupo, con el contenido de cada clúster', () => {
    const [grupo] = deTipo(analizarMarkdown(MUESTRA_ES), 'pestanas') as BloquePestanas[];

    expect(grupo.paneles.map((p) => p.cluster)).toEqual(['apolo2', 'apolo3']);
    expect(html(grupo.paneles[0].bloques)).toContain('<code>longjobs</code>');
    expect(html(grupo.paneles[1].bloques)).toContain('No hay partición por defecto');
  });

  it('una pestaña sola, o dos del mismo clúster, no se juntan con otra', () => {
    const bloques = analizarMarkdown(
      '::: apolo3\n\nSolo tres.\n\n:::\n\n::: apolo3\n\nOtra vez tres.\n\n:::\n',
    );

    const grupos = deTipo(bloques, 'pestanas') as BloquePestanas[];
    expect(grupos.map((g) => g.paneles.map((p) => p.cluster))).toEqual([['apolo3'], ['apolo3']]);
  });

  it('un ::: sin cerrar o de otro nombre queda como texto', () => {
    const bloques = analizarMarkdown('::: apolo4\n\nnada\n\n:::\n\n::: apolo2\n\nsin cierre\n');

    expect(deTipo(bloques, 'pestanas')).toEqual([]);
    expect(html(bloques)).toContain('::: apolo4');
  });

  it('los pasos numerados con comandos quedan como lista con bloques de código', () => {
    const [lista] = deTipo(analizarMarkdown(MUESTRA_ES), 'lista') as BloqueLista[];

    expect(lista.ordenada).toBe(true);
    expect(lista.items).toHaveLength(3);
    const codigos = lista.items.flatMap((item) => deTipo(item, 'codigo') as BloqueCodigo[]);
    expect(codigos.map((c) => c.codigo)).toEqual([
      'cd ~/apolo-training\nnano curso.sh',
      'sbatch -p <partición> curso.sh',
      'apolo-training verificar memoria',
    ]);
  });

  it('una lista sin código sigue siendo HTML', () => {
    const bloques = analizarMarkdown('- uno\n- dos\n');

    expect(bloques).toEqual([{ tipo: 'html', html: '<ul>\n<li>uno</li>\n<li>dos</li>\n</ul>\n' }]);
  });

  it('bash se resalta y se copia; las salidas no se copian', () => {
    const [script, comandos, salida] = deTipo(analizarMarkdown(MUESTRA_ES), 'codigo');

    expect(script.lenguaje).toBe('bash');
    expect(script.html).toContain('<span class="hljs-meta">#!/bin/bash</span>');
    expect(comandos.copiable).toBe(true);
    expect(comandos.codigo).toBe('sbatch <script>.sh\nsqueue -u $USER\nsacct -j <JobID>');
    expect(comandos.html).toContain('sbatch &lt;script&gt;.sh');
    expect(salida.lenguaje).toBe('text');
    expect(salida.copiable).toBe(false);
    expect(bloqueDeCodigo('', 'algo').copiable).toBe(false);
  });

  it('las tablas van en una caja que se desplaza', () => {
    expect(html(analizarMarkdown(MUESTRA_ES))).toMatch(
      /<div class="at-md-tabla" tabindex="0"><table>/,
    );
  });
});

describe('Markdown sin HTML (DoD 3, primera capa)', () => {
  it.each([
    ['<script>alert(1)</script>', '&lt;script&gt;alert(1)&lt;/script&gt;'],
    [
      '<img src="x" onerror="alert(1)">',
      '&lt;img src=&quot;x&quot; onerror=&quot;alert(1)&quot;&gt;',
    ],
    ['<div onclick="alert(1)">x</div>', '&lt;div onclick=&quot;alert(1)&quot;&gt;x&lt;/div&gt;'],
    ['<!-- comentario -->', '&lt;!-- comentario --&gt;'],
    ['ssh <usuario>@apolo', 'ssh &lt;usuario&gt;@apolo'],
  ])('%s se muestra como texto', (entrada, salida) => {
    const resultado = html(analizarMarkdown(entrada));

    expect(resultado).toContain(salida);
    expect(resultado).not.toMatch(/<(script|img|div)\b/);
  });

  it('un enlace javascript: queda solo como texto', () => {
    const resultado = html(analizarMarkdown('[clic](javascript:alert(1))'));

    expect(resultado).toBe('<p>clic</p>\n');
  });

  it('los enlaces externos abren en otra pestaña; los internos no', () => {
    const resultado = html(
      analizarMarkdown('[docs](https://apolo-docs.readthedocs.io) [aquí](/cursos)'),
    );

    expect(resultado).toContain(
      '<a href="https://apolo-docs.readthedocs.io" target="_blank" rel="noopener noreferrer">docs</a>',
    );
    expect(resultado).toContain('<a href="/cursos">aquí</a>');
  });

  it.each([
    ['https://x.org', 'https://x.org'],
    ['mailto:apolo@eafit.edu.co', 'mailto:apolo@eafit.edu.co'],
    ['/cursos', '/cursos'],
    ['#objetivos', '#objetivos'],
    ['javascript:alert(1)', null],
    ['JavaScript:alert(1)', null],
    ['java\nscript:alert(1)', null],
    [' javascript:alert(1)', null],
    ['data:text/html,x', null],
    ['vbscript:x', null],
  ])('urlSegura(%j) = %j', (url, esperada) => {
    expect(urlSegura(url)).toBe(esperada);
  });
});
