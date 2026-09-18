/* Initials and a colour for a user's avatar, both derived from the name so every user gets a
   stable badge without an image. Pure, so node can test it. */

const CAMEL_PARTS = /\p{Lu}+(?!\p{Ll})|\p{Lu}?\p{Ll}+|\p{N}+/gu;

/** One or two upper-case letters: the first letters of the first two words, camel-case words
 * counting as words ("DevLocal" gives "DL"), or the first two letters of a single word. */
export function initials(name) {
  const words = String(name ?? '')
    .split(/[^\p{L}\p{N}]+/u)
    .filter(Boolean);
  if (!words.length) return '?';
  const parts = words.length > 1 ? words : (words[0].match(CAMEL_PARTS) ?? [words[0]]);
  const letters = parts.length > 1 ? parts.slice(0, 2).map((part) => part[0]) : [parts[0].slice(0, 2)];
  return letters.join('').toUpperCase();
}

/** A hue in 0–359 from the name, the same every time. */
export function hueOf(name) {
  let hash = 0;
  for (const char of String(name ?? '')) hash = (hash * 31 + char.codePointAt(0)) >>> 0;
  return hash % 360;
}

/** A background that carries white text in both themes. */
export function avatarColor(name) {
  return `hsl(${hueOf(name)} 50% 42%)`;
}
