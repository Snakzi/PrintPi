import { drawBrand, drawCard, drawLogo, drawPill, drawText, loadImage, measure, prepareCanvas, roundedRect, wrapText } from '../canvas/draw.js';
import { formatClock, formatCost, formatDate, formatDuration, formatEnergy, formatFilament, stripGcodeExtension } from '../format.js';

/**
 * Draws the postcard of a print onto a canvas: name, outcome, the figures and
 * the picture, either the camera's last frame or the slicer's thumbnail. The
 * figures are computed separately so they can be tested without a canvas.
 */
export const WIDTH = 1200;
export const HEIGHT = 630;

/** The state as the card announces it. */
export function outcomeLabel(print) {
  const percent = Math.round((print.progress ?? 0) * 100);
  if (print.state === 'finished') return 'Finished';
  if (print.state === 'cancelled') return `Cancelled at ${percent} %`;
  return `Failed at ${percent} %`;
}

/** Up to four figures for the card, in reading order. */
export function postcardStats(print, { energyPrice = null, currency = '€' } = {}) {
  const stats = [{ label: 'Print time', value: formatDuration(print.elapsed) }];
  if (print.state === 'finished' || !print.total_layers) {
    stats.push({ label: 'Layers', value: String(print.total_layers || print.layers || '–') });
  } else {
    stats.push({ label: 'Layers', value: `${print.layers} / ${print.total_layers}` });
  }
  if (print.filament_g != null || print.filament_mm != null) {
    const cost = print.filament_cost != null ? `${print.filament_cost.toFixed(2)} ${currency}` : null;
    stats.push({ label: 'Filament', value: formatFilament(print.filament_g, print.filament_mm), note: cost });
  }
  if (print.energy_wh != null) {
    stats.push({ label: 'Energy', value: formatEnergy(print.energy_wh), note: formatCost(print.energy_wh, energyPrice, currency) });
  }
  if (stats.length < 4 && print.slicer) {
    stats.push({ label: 'Slicer', value: print.slicer.match(/^[A-Za-z ]+/)?.[0].trim() ?? print.slicer });
  }
  return stats.slice(0, 4);
}

/** Renders the card at twice its nominal size so shared PNGs stay crisp. */
export async function renderPostcard(canvas, print, options = {}) {
  const [cover, thumbnail] = await Promise.all([loadImage(print.cover_url), loadImage(print.thumbnail_url)]);
  const ctx = prepareCanvas(canvas, WIDTH, HEIGHT);

  drawCard(ctx, WIDTH, HEIGHT);
  drawBrand(ctx, 52, 46);
  drawPicture(ctx, { x: 664, y: 52, width: 484, height: 526 }, cover, thumbnail);

  const tone = print.state === 'finished' ? ['#34d399', 'rgba(52, 211, 153, 0.16)'] : print.state === 'cancelled' ? ['#d4d4d8', 'rgba(161, 161, 170, 0.2)'] : ['#fca5a5', 'rgba(239, 68, 68, 0.18)'];
  drawPill(ctx, outcomeLabel(print).toUpperCase(), 52, 118, tone);

  const lines = wrapText(ctx, stripGcodeExtension(print.name), 560, 2, { size: 44, weight: 700 });
  let y = 200;
  for (const line of lines) {
    drawText(ctx, line, 52, y, { size: 44, weight: 700, color: '#fafafa' });
    y += 52;
  }
  const where = [formatDate(print.started_at), options.printerName ?? print.printer].filter(Boolean).join(' · ');
  drawText(ctx, where, 52, y + 6, { size: 18, weight: 400, color: '#a1a1aa' });

  postcardStats(print, options).forEach((stat, index) => {
    const x = 52 + (index % 2) * 290;
    const top = 400 + Math.floor(index / 2) * 96;
    drawText(ctx, stat.label.toUpperCase(), x, top, { size: 12, weight: 600, color: '#71717a', spacing: '1.5px' });
    drawText(ctx, stat.value, x, top + 40, { size: 32, weight: 600, color: '#fafafa' });
    if (stat.note) {
      const width = measure(ctx, stat.value, { size: 32, weight: 600 });
      drawText(ctx, stat.note, x + width + 12, top + 40, { size: 15, weight: 400, color: '#a1a1aa' });
    }
  });

  const times = [print.started_at, print.finished_at].filter(Boolean).map((iso) => formatClock(new Date(iso).getTime()));
  if (times.length) drawText(ctx, times.join(' – '), 52, 596, { size: 14, weight: 400, color: '#52525b' });
  return canvas;
}

function drawPicture(ctx, box, cover, thumbnail) {
  ctx.fillStyle = '#18181b';
  roundedRect(ctx, box.x, box.y, box.width, box.height, 20);
  ctx.fill();
  ctx.save();
  roundedRect(ctx, box.x, box.y, box.width, box.height, 20);
  ctx.clip();
  if (cover) {
    drawCovering(ctx, cover, box);
  } else if (thumbnail) {
    drawContained(ctx, thumbnail, { x: box.x + 32, y: box.y + 32, width: box.width - 64, height: box.height - 64 });
  } else {
    ctx.globalAlpha = 0.25;
    drawLogo(ctx, box.x + box.width / 2 - 80, box.y + box.height / 2 - 80, 160);
    ctx.globalAlpha = 1;
  }
  ctx.restore();
  ctx.strokeStyle = '#27272a';
  ctx.lineWidth = 2;
  roundedRect(ctx, box.x, box.y, box.width, box.height, 20);
  ctx.stroke();

  // With a camera picture the slicer's render becomes an inset, the two are nice side by side.
  if (cover && thumbnail) {
    const inset = { x: box.x + box.width - 166, y: box.y + box.height - 166, width: 150, height: 150 };
    ctx.fillStyle = '#09090b';
    roundedRect(ctx, inset.x, inset.y, inset.width, inset.height, 14);
    ctx.fill();
    ctx.save();
    roundedRect(ctx, inset.x, inset.y, inset.width, inset.height, 14);
    ctx.clip();
    drawContained(ctx, thumbnail, { x: inset.x + 8, y: inset.y + 8, width: inset.width - 16, height: inset.height - 16 });
    ctx.restore();
    ctx.strokeStyle = '#3f3f46';
    ctx.lineWidth = 2;
    roundedRect(ctx, inset.x, inset.y, inset.width, inset.height, 14);
    ctx.stroke();
  }
}

function drawCovering(ctx, image, box) {
  const scale = Math.max(box.width / image.width, box.height / image.height);
  const width = image.width * scale;
  const height = image.height * scale;
  ctx.drawImage(image, box.x + (box.width - width) / 2, box.y + (box.height - height) / 2, width, height);
}

function drawContained(ctx, image, box) {
  const scale = Math.min(box.width / image.width, box.height / image.height);
  const width = image.width * scale;
  const height = image.height * scale;
  ctx.drawImage(image, box.x + (box.width - width) / 2, box.y + (box.height - height) / 2, width, height);
}
