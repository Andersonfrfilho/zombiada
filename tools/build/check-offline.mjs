import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const OUTPUT_DIR = join(ROOT, 'dist');

// Anything here makes a page fetch from the network when it opens.
const BLOCKING_RULES = [
  { name: 'script externo', pattern: /<script[^>]+src=["']https?:\/\//gi },
  { name: 'folha de estilo ou preconnect externo', pattern: /<link[^>]+href=["']https?:\/\//gi },
  { name: 'imagem externa', pattern: /<img[^>]+src=["']https?:\/\//gi },
  { name: '@import externo', pattern: /@import\s+url\(\s*["']?https?:\/\//gi },
  { name: 'fetch para a internet', pattern: /fetch\(\s*["'`]https?:\/\//gi },
  { name: 'link para o Claude', pattern: /https?:\/\/claude\.ai\/artifact/gi },
];
// Allowed offline because the page falls back to the browser when the Claude runtime is absent.
const NOTICE_RULES = [{ name: 'usa window.claude quando existe (offline cai no navegador)', pattern: /window\.claude\.use\(/g }];
const LOCAL_LINK = /<a[^>]+href="([^"#:]+\.html)"/g;

function listHtmlFiles(directory) {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    return statSync(path).isDirectory() ? listHtmlFiles(path) : name.endsWith('.html') ? [path] : [];
  });
}

function countMatches(html, pattern) {
  return (html.match(pattern) ?? []).length;
}

function brokenIndexLinks() {
  const config = JSON.parse(readFileSync(join(ROOT, 'site.config.json'), 'utf8'));
  const pagesDir = join(OUTPUT_DIR, config.pagesBase);
  const indexHtml = readFileSync(join(pagesDir, 'index.html'), 'utf8');
  const linked = [...indexHtml.matchAll(LOCAL_LINK)].map((match) => match[1]);
  const configured = config.sections.flatMap((section) => section.pages.map((page) => page.path));
  const mapped = Object.values(config.artifacts);
  return [...new Set([...linked, ...configured, ...mapped])].filter((path) => !existsSync(join(pagesDir, path)));
}

function main() {
  if (!existsSync(OUTPUT_DIR)) throw new Error('dist/ não existe: rode make site antes.');
  const failures = [];
  const notices = [];
  for (const file of listHtmlFiles(OUTPUT_DIR)) {
    const html = readFileSync(file, 'utf8');
    const path = relative(OUTPUT_DIR, file);
    for (const rule of BLOCKING_RULES) {
      const count = countMatches(html, rule.pattern);
      if (count) failures.push(`${path}: ${count}× ${rule.name}`);
    }
    for (const rule of NOTICE_RULES) {
      if (countMatches(html, rule.pattern)) notices.push(`${path}: ${rule.name}`);
    }
  }
  for (const path of brokenIndexLinks()) failures.push(`índice aponta para ${path}, que não foi gerado`);
  for (const notice of notices) console.log(`aviso  ${notice}`);
  if (failures.length) {
    for (const failure of failures) console.error(`FALHA  ${failure}`);
    process.exitCode = 1;
    return;
  }
  console.log(`offline ok: ${listHtmlFiles(OUTPUT_DIR).length} páginas sem dependência de rede`);
}

main();
