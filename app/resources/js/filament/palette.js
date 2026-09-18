import { formatWeight } from '../format.js';

/**
 * The colour card of the inventory, the picture to send when someone asks
 * "which colours do you have?": one tile per colour and material, ordered
 * like a rainbow with the greys at the end. The layout is computed here so
 * the renderer only draws.
 */

/** Hue, saturation, lightness and chroma (0..360, then 0..1) of a #rrggbb colour, or null. */
export function hexToHsl(hex) {
  const match = /^#?([0-9a-f]{6})$/i.exec(hex ?? '');
  if (!match) return null;
  const [r, g, b] = [0, 2, 4].map((offset) => parseInt(match[1].slice(offset, offset + 2), 16) / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  if (d === 0) return { h: 0, s: 0, l, c: 0 };
  const s = d / (1 - Math.abs(2 * l - 1));
  let h;
  if (max === r) h = ((g - b) / d) % 6;
  else if (max === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;
  return { h: (h * 60 + 360) % 360, s, l, c: d };
}

/** Whether a colour reads as white, grey or black rather than a hue; chroma, not saturation, because
    saturation is inflated near white and black (an off-white still has a hue in HSL terms). */
export function isNeutral(hsl) {
  return hsl.c < 0.1 || hsl.l < 0.07 || hsl.l > 0.95;
}

/**
 * The sort key of a colour: hues in rainbow order starting just before red so
 * every red sits together, then the neutrals from white to black, then no colour.
 */
export function colorOrder(hex) {
  const hsl = hexToHsl(hex);
  if (!hsl) return 2000;
  if (isNeutral(hsl)) return 1000 + (1 - hsl.l) * 100;
  return (hsl.h + 30) % 360;
}

/** Spools of the same colour, finish, material and vendor as one tile, in colour order. */
export function paletteTiles(spools) {
  const tiles = new Map();
  for (const spool of spools) {
    const key = [spool.color, spool.finish, spool.material, spool.vendor].map((part) => (part ?? '').toLowerCase()).join('|');
    const tile = tiles.get(key) ?? {
      color: spool.color ?? null,
      finish: spool.finish ?? null,
      name: spool.name,
      material: spool.material ?? null,
      vendor: spool.vendor ?? null,
      count: 0,
      remaining: 0,
    };
    tile.count += 1;
    tile.remaining += spool.remaining ?? 0;
    tiles.set(key, tile);
  }
  return [...tiles.values()].sort((a, b) => colorOrder(a.color) - colorOrder(b.color));
}

/** How many tiles sit side by side: few spools get big tiles, a large inventory a dense grid. */
export function paletteColumns(count) {
  return Math.min(6, Math.max(2, Math.ceil(Math.sqrt(count * 1.5))));
}

/** The line under the title: spools, materials and what is left altogether. */
export function paletteSummary(spools) {
  const materials = [...new Set(spools.map((spool) => spool.material).filter(Boolean))];
  const grams = spools.reduce((sum, spool) => sum + (spool.remaining ?? 0), 0);
  const parts = [`${spools.length} ${spools.length === 1 ? 'spool' : 'spools'}`];
  if (materials.length > 4) parts.push(`${materials.length} materials`);
  else if (materials.length) parts.push(materials.join(', '));
  parts.push(`${formatWeight(grams)} left`);
  return parts.join(' · ');
}

/**
 * The grid for `count` tiles inside `width`: tile size, gap and rows, so the
 * card's height follows the inventory.
 */
export function paletteLayout(count, width, { gap = 20 } = {}) {
  const columns = paletteColumns(count);
  const rows = Math.max(1, Math.ceil(count / columns));
  const tileWidth = (width - gap * (columns - 1)) / columns;
  const swatchHeight = Math.round(tileWidth * 0.62);
  const text = columns <= 3 ? { name: 22, detail: 15, line: 26 } : columns <= 4 ? { name: 19, detail: 14, line: 23 } : { name: 16, detail: 13, line: 20 };
  const tileHeight = swatchHeight + 26 + text.line * 3 + 6;
  return { columns, rows, gap, tileWidth, tileHeight, swatchHeight, text, height: rows * tileHeight + (rows - 1) * gap };
}
