// Line icons on a 24 × 24 grid, drawn with currentColor so the index can tint them.
export const SECTION_ICONS = {
  site: '<path d="M7 4h10l-8 9h8"/><path d="M6 20c2-3 4-3 6-1s4 2 6-1"/>',
  jogo: '<rect x="2.5" y="7" width="19" height="11" rx="4"/><path d="M7 10.5v4M5 12.5h4"/><circle cx="16" cy="11.5" r=".9"/><circle cx="18" cy="14" r=".9"/>',
  kit: '<path d="M12 3 4 7.5v9L12 21l8-4.5v-9z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/>',
  mapa: '<path d="M3 6.5 9 4l6 2.5L21 4v13.5L15 20l-6-2.5L3 20z"/><path d="M9 4v13.5M15 6.5V20"/>',
  zumbis: '<path d="M5 11a7 7 0 1 1 14 0v3l-2 1v3h-3v-2h-4v2H7v-3l-2-1z"/><circle cx="9" cy="11" r="1.6"/><circle cx="15" cy="11" r="1.6"/>',
  sobreviventes: '<circle cx="12" cy="7" r="3.5"/><path d="M5 21c0-4 3-7 7-7s7 3 7 7"/>',
  armas: '<circle cx="12" cy="12" r="7.5"/><path d="M12 2v5M12 17v5M2 12h5M17 12h5"/><circle cx="12" cy="12" r="1"/>',
  veiculos: '<path d="M3 16v-4l2.5-5h13L21 12v4z"/><path d="M3 12h18"/><circle cx="7.5" cy="16.5" r="2"/><circle cx="16.5" cy="16.5" r="2"/>',
  efeitos: '<path d="M12 3c1 4 6 6 6 11a6 6 0 0 1-12 0c0-3 2-4 2-7 2 1 3 3 3 5 1-2 1-6 1-9z"/>',
  animais: '<circle cx="6" cy="10" r="1.8"/><circle cx="10" cy="6" r="1.8"/><circle cx="14" cy="6" r="1.8"/><circle cx="18" cy="10" r="1.8"/><path d="M8 17c0-3 2-5 4-5s4 2 4 5c0 2-2 3-4 2-2 1-4 0-4-2z"/>',
  vegetacao: '<path d="M5 19c0-8 5-14 15-15-1 10-7 15-15 15z"/><path d="M5 19 13 11"/>',
  arte: '<path d="M12 3a9 9 0 1 0 0 18c1.5 0 2-1 1.5-2.2-.6-1.4.4-2.8 2-2.8H18a3 3 0 0 0 3-3c0-5.5-4-10-9-10z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="15" cy="7.5" r="1"/>',
};

const FAVICON_BACKGROUND = '#e0773f';
const FAVICON_STROKE = '#1a0f08';
const EXISTING_ICON_LINK = /<link[^>]+rel=["'](?:shortcut )?icon["'][^>]*>\s*/gi;

export function iconSvg(sectionId) {
  const paths = SECTION_ICONS[sectionId] ?? SECTION_ICONS.site;
  return `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
}

function faviconDataUri(sectionId) {
  const paths = SECTION_ICONS[sectionId] ?? SECTION_ICONS.site;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="${FAVICON_BACKGROUND}"/><g transform="translate(4 4)" fill="none" stroke="${FAVICON_STROKE}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">${paths}</g></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

export function addFavicon({ html, sectionId }) {
  const link = `<link rel="icon" type="image/svg+xml" href="${faviconDataUri(sectionId)}">`;
  const cleaned = html.replace(EXISTING_ICON_LINK, '');
  if (/<head[^>]*>/i.test(cleaned)) return cleaned.replace(/<head[^>]*>/i, (head) => `${head}\n${link}`);
  return `${link}\n${cleaned}`;
}
