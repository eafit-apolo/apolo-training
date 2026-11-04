import hljs from 'highlight.js/lib/core';
import bash from 'highlight.js/lib/languages/bash';
import type { RendererObject, Token, TokenizerAndRendererExtension, Tokens } from 'marked';
import { Marked, Renderer } from 'marked';
import type { Cluster } from '../../../core/sesion/sesion';

/**
 * El Markdown de una lección (C-01) partido en bloques que la vista pinta con
 * componentes propios (F-04): el texto como HTML, y los bloques de código y
 * las pestañas Apolo II / Apolo III como componentes, para que tengan botón de
 * copiar y se usen con el teclado.
 *
 * Seguridad, en dos capas: aquí el HTML que traiga el Markdown se muestra como
 * texto (no se interpreta) y los enlaces solo aceptan http, https, mailto o
 * rutas relativas; después Angular sanitiza todo lo que entra por `innerHTML`.
 */

hljs.registerLanguage('bash', bash);

/** Texto, encabezados, tablas… ya convertidos a HTML (lo sanitiza Angular al pintarlo). */
export interface BloqueHtml {
  readonly tipo: 'html';
  readonly html: string;
}

export interface BloqueCodigo {
  readonly tipo: 'codigo';
  /** `bash`, `text`… o vacío si el bloque no lo dice. */
  readonly lenguaje: string;
  /** Lo que se copia, tal cual. */
  readonly codigo: string;
  /** El código escapado y, en bash, resaltado. */
  readonly html: string;
  /** Las salidas (`text`) y los bloques sin lenguaje no se copian. */
  readonly copiable: boolean;
}

/** Una lista con código dentro: cada ítem son bloques (las demás listas van como HTML). */
export interface BloqueLista {
  readonly tipo: 'lista';
  readonly ordenada: boolean;
  readonly inicio: number;
  readonly items: readonly (readonly Bloque[])[];
}

export interface BloqueCita {
  readonly tipo: 'cita';
  readonly bloques: readonly Bloque[];
}

export interface Panel {
  readonly cluster: Cluster;
  readonly bloques: readonly Bloque[];
}

/** `::: apolo2` y `::: apolo3` seguidos: un grupo de pestañas. */
export interface BloquePestanas {
  readonly tipo: 'pestanas';
  readonly paneles: readonly Panel[];
}

export type Bloque = BloqueHtml | BloqueCodigo | BloqueLista | BloqueCita | BloquePestanas;

/** Se resaltan con la gramática de bash. */
const LENGUAJES_BASH = new Set(['bash', 'sh', 'shell', 'zsh']);
/** Salidas de comandos: se muestran sin botón de copiar. */
const SIN_COPIAR = new Set(['', 'text', 'txt', 'plaintext', 'output', 'console']);
/** Esquemas permitidos en enlaces e imágenes; sin esquema es una ruta relativa. */
const ESQUEMAS = new Set(['http', 'https', 'mailto']);

const ESCAPES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

export function escapar(texto: string): string {
  return texto.replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

/**
 * La URL si es segura, sin espacios ni caracteres de control (el navegador los
 * ignora, así que `java\nscript:` sería `javascript:`); `null` si no.
 */
export function urlSegura(href: string): string | null {
  // eslint-disable-next-line no-control-regex
  const limpia = href.replace(/[\u0000- \u007f]/g, '');
  const esquema = /^([a-z][a-z0-9+.-]*):/i.exec(limpia)?.[1]?.toLowerCase();
  return esquema === undefined || ESQUEMAS.has(esquema) ? limpia : null;
}

interface TokenPestana extends Tokens.Generic {
  readonly type: 'pestana';
  readonly cluster: Cluster;
  readonly tokens: Token[];
}

// `::: apolo2`, el contenido y `:::` en una línea sola (content/README.md).
const PESTANA = /^ {0,3}::: *(apolo2|apolo3) *\n([\s\S]*?)\n {0,3}::: *(?:\n+|$)/;

const pestanas: TokenizerAndRendererExtension = {
  name: 'pestana',
  level: 'block',
  start: (src) => /^ {0,3}::: *apolo[23]\b/m.exec(src)?.index,
  tokenizer(src) {
    const encontrada = PESTANA.exec(src);
    if (!encontrada) {
      return undefined;
    }
    const token: TokenPestana = {
      type: 'pestana',
      raw: encontrada[0],
      cluster: encontrada[1] as Cluster,
      tokens: this.lexer.blockTokens(encontrada[2], []),
    };
    return token;
  },
  // `convertir()` saca las pestañas antes de llegar aquí; por si acaso, el contenido.
  renderer(token) {
    return this.parser.parse((token as TokenPestana).tokens);
  },
};

const renderer: RendererObject = {
  // HTML crudo del Markdown: se muestra como texto (decisión del 4-nov).
  html({ text, block }) {
    const visible = escapar(block ? text.trim() : text);
    return block ? `<p>${visible}</p>\n` : visible;
  },
  link({ href, title, tokens }) {
    const texto = this.parser.parseInline(tokens);
    const url = urlSegura(href);
    if (url === null) {
      return texto;
    }
    const titulo = title ? ` title="${escapar(title)}"` : '';
    const externo = /^https?:/i.test(url) ? ' target="_blank" rel="noopener noreferrer"' : '';
    return `<a href="${escapar(url)}"${titulo}${externo}>${texto}</a>`;
  },
  image({ href, text }) {
    return urlSegura(href) === null ? escapar(text) : false;
  },
  // Sin <input> (Angular lo quitaría): las tareas de GFM como caracteres.
  checkbox({ checked }) {
    return checked ? '☑ ' : '☐ ';
  },
  // Las tablas anchas se desplazan dentro de su caja, también con el teclado.
  table(token) {
    return `<div class="at-md-tabla" tabindex="0">${Renderer.prototype.table.call(this, token)}</div>\n`;
  },
};

const md = new Marked({ gfm: true, async: false, extensions: [pestanas], renderer });

export function bloqueDeCodigo(lenguaje: string, codigo: string): BloqueCodigo {
  const html = LENGUAJES_BASH.has(lenguaje)
    ? hljs.highlight(codigo, { language: 'bash', ignoreIllegals: true }).value
    : escapar(codigo);
  return { tipo: 'codigo', lenguaje, codigo, html, copiable: !SIN_COPIAR.has(lenguaje) };
}

/** Si dentro hay código o pestañas, que deben ser componentes. */
function tieneComponentes(token: Token): boolean {
  switch (token.type) {
    case 'code':
    case 'pestana':
      return true;
    case 'list':
      return (token as Tokens.List).items.some((item) => item.tokens.some(tieneComponentes));
    case 'blockquote':
      return (token as Tokens.Blockquote).tokens.some(tieneComponentes);
    default:
      return false;
  }
}

function convertir(tokens: readonly Token[]): Bloque[] {
  const bloques: Bloque[] = [];
  let html: Token[] = [];
  const cerrarHtml = () => {
    if (html.some((t) => t.type !== 'space')) {
      bloques.push({ tipo: 'html', html: md.Parser.parse(html, md.defaults) });
    }
    html = [];
  };

  let i = 0;
  while (i < tokens.length) {
    const token = tokens[i];
    i++;
    if (!tieneComponentes(token)) {
      html.push(token);
      continue;
    }
    cerrarHtml();
    if (token.type === 'code') {
      const codigo = token as Tokens.Code;
      const lenguaje = (codigo.lang ?? '').trim().split(/\s+/)[0].toLowerCase();
      bloques.push(bloqueDeCodigo(lenguaje, codigo.text));
    } else if (token.type === 'pestana') {
      // Las pestañas seguidas (con líneas en blanco entre ellas) forman un grupo.
      const paneles: Panel[] = [panel(token as TokenPestana)];
      let j = i;
      while (j < tokens.length && tokens[j].type === 'space') {
        j++;
      }
      while (j < tokens.length && tokens[j].type === 'pestana') {
        const otra = tokens[j] as TokenPestana;
        if (paneles.some((p) => p.cluster === otra.cluster)) {
          break;
        }
        paneles.push(panel(otra));
        i = j + 1;
        j = i;
        while (j < tokens.length && tokens[j].type === 'space') {
          j++;
        }
      }
      bloques.push({ tipo: 'pestanas', paneles });
    } else if (token.type === 'list') {
      const lista = token as Tokens.List;
      bloques.push({
        tipo: 'lista',
        ordenada: lista.ordered,
        inicio: typeof lista.start === 'number' ? lista.start : 1,
        items: lista.items.map((item) => convertir(item.tokens)),
      });
    } else {
      bloques.push({ tipo: 'cita', bloques: convertir((token as Tokens.Blockquote).tokens) });
    }
  }
  cerrarHtml();
  return bloques;
}

function panel(token: TokenPestana): Panel {
  return { cluster: token.cluster, bloques: convertir(token.tokens) };
}

/** El Markdown de una lección, listo para `<at-bloques>`. */
export function analizarMarkdown(texto: string): Bloque[] {
  return convertir(md.Lexer.lex(texto, md.defaults));
}
