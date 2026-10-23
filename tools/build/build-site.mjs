import { copyFileSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildKitPage } from './lib/build-kit.mjs';
import { loadFontFaces } from './lib/fonts.mjs';
import { renderIndex } from './lib/render-index.mjs';
import { transformPage } from './lib/transform-page.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const SITE_DIR = join(ROOT, 'site');
const PAGES_DIR = join(SITE_DIR, 'pages');
const OUTPUT_DIR = join(ROOT, 'dist');
const VENDOR_DIR = join(ROOT, 'vendor');
const PORTAL_SOURCE = join(SITE_DIR, 'portal', 'portal-equipes.html');
const PORTAL_OUTPUTS = ['index.html', 'portal/portal-equipes.html'];
// The portal builds its file links as "../" + path, which resolves to the site root from both outputs.
const PORTAL_LINK_PREFIX = '../';

function listFiles(directory) {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    return statSync(path).isDirectory() ? listFiles(path) : [path];
  });
}

function writeOutput(relativePath, html) {
  const target = join(OUTPUT_DIR, relativePath);
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, html);
  return Buffer.byteLength(html);
}

function copyAsset({ source, relativePath }) {
  const target = join(OUTPUT_DIR, relativePath);
  mkdirSync(dirname(target), { recursive: true });
  copyFileSync(source, target);
}

function linkPrefixFor(pagePath) {
  return '../'.repeat(pagePath.split('/').length - 1);
}

function buildDateLabel(date) {
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'America/Sao_Paulo' });
}

function buildPages({ config, context, sectionByPath }) {
  const pages = [];
  const base = config.pagesBase;
  const kit = buildKitPage({ templatePath: join(SITE_DIR, config.kit.template), galleryPath: join(PAGES_DIR, config.kit.librarySource) });
  const kitHtml = transformPage({ html: kit.html, context, sectionId: 'kit', linkPrefix: linkPrefixFor(config.kit.output) });
  pages.push({ path: `${base}/${config.kit.output}`, bytes: writeOutput(`${base}/${config.kit.output}`, kitHtml) });
  for (const source of listFiles(PAGES_DIR)) {
    const path = relative(PAGES_DIR, source);
    if (!path.endsWith('.html')) {
      copyAsset({ source, relativePath: `${base}/${path}` });
      continue;
    }
    const html = transformPage({ html: readFileSync(source, 'utf8'), context, sectionId: sectionByPath.get(path) ?? 'site', linkPrefix: linkPrefixFor(path) });
    pages.push({ path: `${base}/${path}`, bytes: writeOutput(`${base}/${path}`, html) });
  }
  return { pages, kitBuilders: kit.builderCount };
}

function buildPortal(context) {
  const source = readFileSync(PORTAL_SOURCE, 'utf8');
  const linkPrefix = `${PORTAL_LINK_PREFIX}docs/offline/`;
  return PORTAL_OUTPUTS.map((path) => ({ path, bytes: writeOutput(path, transformPage({ html: source, context, sectionId: 'site', linkPrefix })) }));
}

function main() {
  const config = JSON.parse(readFileSync(join(ROOT, 'site.config.json'), 'utf8'));
  const report = { unresolvedScripts: new Set(), missingFonts: new Set(), unmappedArtifacts: new Set() };
  const context = { vendorDir: VENDOR_DIR, faces: loadFontFaces(VENDOR_DIR), report, artifacts: config.artifacts };
  const sectionByPath = new Map(config.sections.flatMap((section) => section.pages.map((page) => [page.path, section.id])));

  rmSync(OUTPUT_DIR, { recursive: true, force: true });
  const { pages, kitBuilders } = buildPages({ config, context, sectionByPath });
  pages.push(...buildPortal(context));

  const now = new Date();
  const indexHtml = renderIndex({ templatePath: join(SITE_DIR, 'templates', 'index.template.html'), config, buildDate: buildDateLabel(now) });
  const indexPath = `${config.pagesBase}/index.html`;
  pages.push({ path: indexPath, bytes: writeOutput(indexPath, transformPage({ html: indexHtml, context, sectionId: 'site', linkPrefix: '' })) });
  writeFileSync(join(OUTPUT_DIR, 'build-info.json'), JSON.stringify({ builtAt: now.toISOString(), kitBuilders, pages }, null, 1));

  const sources = listFiles(PAGES_DIR).map((path) => relative(PAGES_DIR, path)).filter((path) => path.endsWith('.html'));
  const unlisted = sources.filter((path) => !sectionByPath.has(path));
  console.log(`dist/ gerado: ${pages.length} páginas, ${(pages.reduce((sum, page) => sum + page.bytes, 0) / 1e6).toFixed(1)} MB`);
  if (unlisted.length) console.warn(`Páginas fora do índice (acrescente em site.config.json): ${unlisted.join(', ')}`);
  if (report.missingFonts.size) console.warn(`Fontes sem cópia em vendor/fonts: ${[...report.missingFonts].join(', ')}`);
  if (report.unresolvedScripts.size) console.warn(`Scripts externos sem cópia em vendor/: ${[...report.unresolvedScripts].join(', ')}`);
  if (report.unmappedArtifacts.size) console.warn(`Artefatos sem página local (acrescente em "artifacts" do site.config.json): ${[...report.unmappedArtifacts].join(', ')}`);
}

main();
