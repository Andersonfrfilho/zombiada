import { readFileSync } from 'node:fs';

import { iconSvg } from './icons.mjs';

function sectionsAsTeams(sections) {
  return sections.map(({ id, name, pages }) => [
    id,
    name,
    pages.map(({ path, title, description, tags }) => [path, title, description, tags]),
  ]);
}

export function renderIndex({ templatePath, config, buildDate }) {
  const template = readFileSync(templatePath, 'utf8');
  return template
    .replace('/*@@TEAMS@@*/[]', () => JSON.stringify(sectionsAsTeams(config.sections), null, 1))
    .replace('/*@@FILTERS@@*/[]', () => JSON.stringify(config.filters))
    .replace('/*@@ICONS@@*/{}', () => JSON.stringify(Object.fromEntries(config.sections.map(({ id }) => [id, iconSvg(id)]))))
    .replace('{{SITE_ICON}}', () => iconSvg('site'))
    .replace('{{BUILD_DATE}}', buildDate)
    .replace('{{SITE_TITLE}}', config.title);
}
