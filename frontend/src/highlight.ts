/** Split source text around the first occurrence of `match` for highlighting. */
export function splitHighlight(source: string, match: string): [string, string, string] {
  if (!source) return ['', '', ''];
  const needle = (match || '').trim();
  if (!needle || needle.length < 4) return [source, '', ''];
  const idx = source.toLowerCase().indexOf(needle.toLowerCase());
  if (idx < 0) {
    // Fall back to first 8-word window of the match.
    const words = needle.split(/\s+/).slice(0, 8).join(' ');
    if (words.length < 8) return [source, '', ''];
    const j = source.toLowerCase().indexOf(words.toLowerCase());
    if (j < 0) return [source, '', ''];
    return [source.slice(0, j), source.slice(j, j + words.length), source.slice(j + words.length)];
  }
  return [source.slice(0, idx), source.slice(idx, idx + needle.length), source.slice(idx + needle.length)];
}
