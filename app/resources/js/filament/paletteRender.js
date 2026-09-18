import { drawBrand, drawCard, drawGlitter, drawText, measure, prepareCanvas, roundedRect, wrapText } from '../canvas/draw.js';
import { formatDate, formatWeight } from '../format.js';
import { paletteLayout, paletteSummary, paletteTiles } from './palette.js';
import { spoolDetail } from './spools.js';

/**
 * Draws the colour card onto a canvas: the brand, a title line and one tile
 * per colour with its name, vendor, material and what is left of it. The card
 * is as tall as the inventory needs.
 */
export const WIDTH = 1200;
const PADDING = 52;
const GRID_TOP = 236;

export function paletteHeight(spools) {
  const tiles = paletteTiles(spools);
  return GRID_TOP + paletteLayout(tiles.length, WIDTH - 2 * PADDING).height + PADDING;
}

export function renderPalette(canvas, spools, { title = 'Filament colours', date = new Date() } = {}) {
  const tiles = paletteTiles(spools);
  const layout = paletteLayout(tiles.length, WIDTH - 2 * PADDING);
  const height = GRID_TOP + layout.height + PADDING;
  const ctx = prepareCanvas(canvas, WIDTH, height);

  drawCard(ctx, WIDTH, height);
  drawBrand(ctx, PADDING, 46);
  drawText(ctx, formatDate(date.toISOString()), WIDTH - PADDING, 77, { size: 16, weight: 400, color: '#71717a', align: 'right' });
  drawText(ctx, title, PADDING, 160, { size: 40, weight: 700, color: '#fafafa' });
  drawText(ctx, spools.length ? paletteSummary(spools) : 'No spools yet', PADDING, 194, { size: 18, weight: 400, color: '#a1a1aa' });

  tiles.forEach((tile, index) => {
    const x = PADDING + (index % layout.columns) * (layout.tileWidth + layout.gap);
    const y = GRID_TOP + Math.floor(index / layout.columns) * (layout.tileHeight + layout.gap);
    drawTile(ctx, tile, x, y, layout);
  });
  return canvas;
}

function drawTile(ctx, tile, x, y, { tileWidth, tileHeight, swatchHeight, text }) {
  ctx.fillStyle = '#18181b';
  roundedRect(ctx, x, y, tileWidth, tileHeight, 18);
  ctx.fill();
  ctx.strokeStyle = '#27272a';
  ctx.lineWidth = 1.5;
  roundedRect(ctx, x, y, tileWidth, tileHeight, 18);
  ctx.stroke();

  drawSwatch(ctx, tile, { x: x + 10, y: y + 10, width: tileWidth - 20, height: swatchHeight - 10 });
  if (tile.count > 1) drawCount(ctx, `×${tile.count}`, x + tileWidth - 22, y + 22);

  const left = x + 16;
  const maxWidth = tileWidth - 32;
  let line = y + swatchHeight + 26;
  const [name] = wrapText(ctx, tile.name, maxWidth, 1, { size: text.name, weight: 600 });
  drawText(ctx, name, left, line, { size: text.name, weight: 600, color: '#fafafa' });
  line += text.line;
  const [detail] = wrapText(ctx, spoolDetail(tile) || '–', maxWidth, 1, { size: text.detail, weight: 400 });
  drawText(ctx, detail, left, line, { size: text.detail, weight: 400, color: '#a1a1aa' });
  line += text.line;
  drawText(ctx, `${formatWeight(tile.remaining)} left`, left, line, { size: text.detail, weight: 400, color: '#71717a' });
}

/** The colour as a block of material with its sparkle and a soft shine, or a dashed grey block without a colour. */
function drawSwatch(ctx, { color, finish }, box) {
  roundedRect(ctx, box.x, box.y, box.width, box.height, 12);
  ctx.fillStyle = color ?? '#3f3f46';
  ctx.fill();
  if (color && finish === 'glitter') drawGlitter(ctx, box, 12, Math.round(box.x + box.y));
  if (color) {
    const shine = ctx.createLinearGradient(box.x, box.y, box.x + box.width, box.y + box.height);
    shine.addColorStop(0, 'rgba(255, 255, 255, 0.22)');
    shine.addColorStop(0.5, 'rgba(255, 255, 255, 0)');
    shine.addColorStop(1, 'rgba(0, 0, 0, 0.18)');
    ctx.fillStyle = shine;
    ctx.fill();
  }
  ctx.save();
  ctx.strokeStyle = color ? 'rgba(255, 255, 255, 0.14)' : '#71717a';
  ctx.lineWidth = 1.5;
  if (!color) ctx.setLineDash([6, 5]);
  roundedRect(ctx, box.x + 0.75, box.y + 0.75, box.width - 1.5, box.height - 1.5, 11.5);
  ctx.stroke();
  ctx.restore();
}

function drawCount(ctx, label, right, y) {
  const style = { size: 13, weight: 700, color: '#fafafa' };
  const width = measure(ctx, label, style) + 18;
  ctx.fillStyle = 'rgba(9, 9, 11, 0.75)';
  roundedRect(ctx, right - width, y - 12, width, 24, 12);
  ctx.fill();
  drawText(ctx, label, right - width / 2, y + 5, { ...style, align: 'center' });
}
