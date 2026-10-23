import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const GOOGLE_FONTS_LINK = /<link[^>]+href=["']https:\/\/fonts\.googleapis\.com\/css2\?([^"']+)["'][^>]*>/g;
const PRECONNECT_LINK = /<link[^>]+rel=["']preconnect["'][^>]*>\s*/g;

export function loadFontFaces(vendorDir) {
  const fontsDir = join(vendorDir, 'fonts');
  const faces = JSON.parse(readFileSync(join(fontsDir, 'fonts.json'), 'utf8'));
  return faces.map((face) => ({ ...face, path: join(fontsDir, face.file) }));
}

function familiesFromQuery(query) {
  return new URLSearchParams(query.replace(/&amp;/g, '&'))
    .getAll('family')
    .map((value) => value.split(':')[0].replace(/\+/g, ' '));
}

// Google serves variable fonts as one file per subset for every weight, so one rule covers the weight range.
function fontFaceCss(faceGroup) {
  const [face] = faceGroup;
  const weights = faceGroup.map((item) => item.weight);
  const weightRange = weights.length > 1 ? `${Math.min(...weights)} ${Math.max(...weights)}` : `${face.weight}`;
  const base64 = readFileSync(face.path).toString('base64');
  return `@font-face{font-family:'${face.family}';font-style:normal;font-weight:${weightRange};font-display:swap;src:url(data:font/woff2;base64,${base64}) format('woff2');unicode-range:${face.unicodeRange}}`;
}

// Swaps each Google Fonts <link> for the same faces embedded from vendor/fonts.
export function inlineGoogleFonts({ html, faces, missing }) {
  const withoutPreconnect = html.replace(PRECONNECT_LINK, '');
  return withoutPreconnect.replace(GOOGLE_FONTS_LINK, (_link, query) => {
    const groupsByFile = new Map();
    for (const family of familiesFromQuery(query)) {
      const matching = faces.filter((face) => face.family === family);
      if (!matching.length) missing.add(family);
      for (const face of matching) groupsByFile.set(face.file, [...(groupsByFile.get(face.file) ?? []), face]);
    }
    const css = [...groupsByFile.values()].map(fontFaceCss);
    return `<style>${css.join('\n')}</style>`;
  });
}
