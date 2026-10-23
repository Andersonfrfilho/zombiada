const ARTIFACT_URL = /https:\/\/claude\.ai\/artifact\/(\w+)/g;

// Points every published-artifact URL at its offline copy; unknown ids stay and fail the offline check.
export function rewriteArtifactLinks({ html, artifacts, prefix, unmapped }) {
  return html.replace(ARTIFACT_URL, (url, id) => {
    const path = artifacts[id];
    if (!path) {
      unmapped.add(id);
      return url;
    }
    return `${prefix}${path}`;
  });
}
