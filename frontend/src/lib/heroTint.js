// Wash colour behind collection headers, picked from the real cover palette.
//
// CollectionHero used to tint from a name-hash hue, which often mismatched
// the artwork. `heroTintColor` prefers the extracted palette primary and
// returns null when there is no palette, so the caller keeps its legacy
// fallback. Pure, like panels.js.
export function heroTintColor(palette) {
  const primary = palette?.primary
  if (!primary) return null
  return `color-mix(in srgb, ${primary} 55%, transparent)`
}
