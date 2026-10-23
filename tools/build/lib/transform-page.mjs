import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { rewriteArtifactLinks } from './artifact-links.mjs';
import { inlineGoogleFonts } from './fonts.mjs';
import { addFavicon } from './icons.mjs';

const VENDOR_SCRIPTS = [
  { pattern: /three(?:\.js)?\/r128\/three\.min\.js$/, file: 'three/three-r128.min.js' },
  { pattern: /^vendor\/three\/three-r128\.min\.js$/, file: 'three/three-r128.min.js' },
];
const EXTERNAL_SCRIPT_TAG = /<script([^>]*)\ssrc=["']([^"']+)["']([^>]*)><\/script>/g;
const CLAUDE_ORIGINAL_NOTE = /\s*Original online:\s*<a href=["']https:\/\/claude\.ai[^"']*["'][^>]*>[^<]*<\/a>\.?/g;
const ONLINE_BADGE = /<a class=["']on["'] href=["']https:\/\/claude\.ai[^"']*["'][^>]*>online<\/a>/g;
const CLAUDE_LINK = /<a\s[^>]*href=["']https:\/\/claude\.ai[^"']*["'][^>]*>([\s\S]*?)<\/a>/g;
const CLAUDE_DOCS_MENTION = /\s*\(Claude Docs\)/g;
const CLAUDE_META = /<meta name=["']claude:[^"']*["'][^>]*>\s*/g;
const HAS_DOCTYPE = /^\s*<!doctype html>/i;

function inlineVendorScripts({ html, vendorDir, unresolved }) {
  return html.replace(EXTERNAL_SCRIPT_TAG, (tag, _before, source) => {
    const vendorScript = VENDOR_SCRIPTS.find(({ pattern }) => pattern.test(source));
    if (!vendorScript) {
      unresolved.add(source);
      return tag;
    }
    const code = readFileSync(join(vendorDir, vendorScript.file), 'utf8');
    return `<script>/* ${vendorScript.file} (cópia offline) */\n${code}</script>`;
  });
}

function removeClaudeReferences(html) {
  return html
    .replace(CLAUDE_ORIGINAL_NOTE, '')
    .replace(ONLINE_BADGE, '')
    .replace(CLAUDE_LINK, '$1')
    .replace(CLAUDE_DOCS_MENTION, '')
    .replace(CLAUDE_META, '');
}

// Pages authored as Claude artifacts have no document skeleton; a file opened from disk needs one.
function ensureSkeleton(html) {
  if (HAS_DOCTYPE.test(html)) return html;
  return `<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n</head>\n<body>\n${html}\n</body>\n</html>\n`;
}

export function transformPage({ html, context, sectionId, linkPrefix }) {
  const { vendorDir, faces, report, artifacts } = context;
  const withLinks = rewriteArtifactLinks({ html, artifacts, prefix: linkPrefix, unmapped: report.unmappedArtifacts });
  const withScripts = inlineVendorScripts({ html: withLinks, vendorDir, unresolved: report.unresolvedScripts });
  const withFonts = inlineGoogleFonts({ html: withScripts, faces, missing: report.missingFonts });
  return addFavicon({ html: ensureSkeleton(removeClaudeReferences(withFonts)), sectionId });
}
