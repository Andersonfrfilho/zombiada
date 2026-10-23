import { readFileSync } from 'node:fs';

// Builders the kit takes straight from the Galeria do Vale Cinzento, so a change there reaches the kit on the next build.
export const KIT_BUILDER_NAMES = `rng rbox bx cyl cone prismGeo prism plane line item flush texText sign blood fire smoke figGeo figure gait zombie human dog
sofa bed table shelf shelfItems rack fridge stove counter wardrobe tv desk locker crate barrel car bus lampPost sandbags fence tent pine tree
windowsOn building house room wl backWin leftWin glass container silo tractor watchtower gondola rifle bars stretcher cot
poleLED poleConcrete poleIron poleWood floodTower sobrado laje colonial chalet companyHouse stilt farmhouse`.split(/\s+/);

const SCRIPT_BLOCK = /<script[^>]*>([\s\S]*?)<\/script>/g;
const SCENE_ENTRY = /\{id:'[^']+',g:'[^']+',n:'([^']+)'[^\n]*?,b:(build\w+)\}/g;
const TOP_LEVEL_DEFINITION = /^(?:function\s+(\w+)\s*\(|const\s+(\w+)\s*=)/;

function findGalleryScript(html) {
  const scripts = [...html.matchAll(SCRIPT_BLOCK)].map((match) => match[1]);
  const gallery = scripts.find((code) => code.includes('const SCENES=['));
  if (!gallery) throw new Error('Galeria sem a lista SCENES: o kit não consegue achar as peças.');
  return gallery.split('\n');
}

// A definition runs until the next line that starts at column 0; a lone "}" closes it.
function collectDefinitions(lines) {
  const definitions = new Map();
  for (let index = 0; index < lines.length; index++) {
    const match = TOP_LEVEL_DEFINITION.exec(lines[index]);
    if (!match) continue;
    const body = [lines[index]];
    let next = index + 1;
    while (next < lines.length && (/^[ \t]/.test(lines[next]) || lines[next].trim() === '}')) {
      body.push(lines[next]);
      next++;
      if (lines[next - 1].trim() === '}') break;
    }
    definitions.set(match[1] ?? match[2], body.join('\n'));
  }
  return definitions;
}

function callsIn(code, names) {
  return names.filter((name) => new RegExp(`(?<![\\w.])${name}\\(`).test(code));
}

function reachableFrom({ start, definitions, names }) {
  const seen = new Set([start]);
  const queue = [start];
  while (queue.length) {
    const code = definitions.get(queue.shift()) ?? '';
    for (const called of callsIn(code, names)) {
      if (seen.has(called)) continue;
      seen.add(called);
      queue.push(called);
    }
  }
  return seen;
}

function mapUsesToScenes({ galleryCode, definitions }) {
  const names = [...definitions.keys()];
  const uses = {};
  const scenes = new Map([...galleryCode.matchAll(SCENE_ENTRY)].map((match) => [match[2], match[1]]));
  for (const [builder, sceneName] of scenes) {
    for (const reached of reachableFrom({ start: builder, definitions, names })) {
      if (!KIT_BUILDER_NAMES.includes(reached)) continue;
      uses[reached] = [...new Set([...(uses[reached] ?? []), sceneName])];
    }
  }
  return uses;
}

export function buildKitPage({ templatePath, galleryPath }) {
  const lines = findGalleryScript(readFileSync(galleryPath, 'utf8'));
  const definitions = collectDefinitions(lines);
  const missing = KIT_BUILDER_NAMES.filter((name) => !definitions.has(name));
  if (missing.length) throw new Error(`Funções sumiram da galeria: ${missing.join(', ')}`);
  const library = KIT_BUILDER_NAMES.map((name) => definitions.get(name)).join('\n');
  const uses = mapUsesToScenes({ galleryCode: lines.join('\n'), definitions });
  const template = readFileSync(templatePath, 'utf8');
  return {
    html: template.replace('/*@@LIB@@*/', () => library).replace('/*@@USES@@*/{}', () => JSON.stringify(uses)),
    builderCount: KIT_BUILDER_NAMES.length,
  };
}
