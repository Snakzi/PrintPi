/**
 * Canvas primitives shared by every card PrintPi renders for sharing: the dark
 * card with its glow, the logo, text with letter spacing and word wrapping.
 */
export const FONT = 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';

export function loadImage(url) {
  if (!url) return Promise.resolve(null);
  return new Promise((resolve) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => resolve(null);
    image.src = url;
  });
}

/** Sizes the canvas at twice its nominal size so shared PNGs stay crisp and returns the scaled context. */
export function prepareCanvas(canvas, width, height, scale = 2) {
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext('2d');
  ctx.scale(scale, scale);
  return ctx;
}

/** The card itself: near-black, an emerald glow in the top left corner and a hairline border. */
export function drawCard(ctx, width, height) {
  ctx.fillStyle = '#09090b';
  roundedRect(ctx, 0, 0, width, height, 28);
  ctx.fill();
  const glow = ctx.createRadialGradient(80, 40, 0, 80, 40, 720);
  glow.addColorStop(0, 'rgba(52, 211, 153, 0.22)');
  glow.addColorStop(1, 'rgba(52, 211, 153, 0)');
  ctx.fillStyle = glow;
  roundedRect(ctx, 0, 0, width, height, 28);
  ctx.fill();
  ctx.strokeStyle = '#27272a';
  ctx.lineWidth = 2;
  roundedRect(ctx, 1, 1, width - 2, height - 2, 27);
  ctx.stroke();
}

/** The logo with the word mark next to it, as every card carries it in the top left corner. */
export function drawBrand(ctx, x, y) {
  drawLogo(ctx, x, y, 44);
  drawText(ctx, 'PrintPi', x + 56, y + 31, { size: 24, weight: 600, color: '#f4f4f5' });
}

/** The PrintPi logo: a nozzle finishing the top layer of a pi built from printed layers. */
export function drawLogo(ctx, x, y, size) {
  const s = size / 128;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(s, s);
  ctx.fillStyle = '#18181b';
  roundedRect(ctx, 0, 0, 128, 128, 28);
  ctx.fill();
  ctx.strokeStyle = '#3f3f46';
  ctx.lineWidth = 1.5;
  roundedRect(ctx, 1, 1, 126, 126, 27);
  ctx.stroke();
  ctx.fillStyle = '#d4d4d8';
  roundedRect(ctx, 75, 12, 28, 14, 2);
  ctx.fill();
  ctx.fillStyle = '#e0b04a';
  ctx.beginPath();
  ctx.moveTo(77, 26);
  ctx.lineTo(101, 26);
  ctx.lineTo(101, 29);
  ctx.lineTo(92.5, 43);
  ctx.lineTo(85.5, 43);
  ctx.lineTo(77, 29);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = '#34d399';
  for (const [rx, ry, w, h] of [
    [27, 46, 72, 10],
    [39, 58, 14, 10],
    [39, 70, 14, 10],
    [38, 82, 15, 10],
    [36, 94, 17, 10],
    [31, 106, 22, 10],
    [73, 58, 14, 10],
    [73, 70, 14, 10],
    [73, 82, 14, 10],
    [73, 94, 14, 10],
    [73, 106, 14, 10],
  ]) {
    roundedRect(ctx, rx, ry, w, h, 3);
    ctx.fill();
  }
  ctx.restore();
}

export function drawPill(ctx, text, x, y, [color, background]) {
  const width = measure(ctx, text, { size: 13, weight: 700, spacing: '1.5px' }) + 28;
  ctx.fillStyle = background;
  roundedRect(ctx, x, y - 20, width, 30, 15);
  ctx.fill();
  drawText(ctx, text, x + 14, y + 1, { size: 13, weight: 700, color, spacing: '1.5px' });
  return width;
}

export function font({ size, weight = 400 }) {
  return `${weight} ${size}px ${FONT}`;
}

/** style: { size, weight, color, spacing, align }. */
export function drawText(ctx, text, x, y, style) {
  ctx.font = font(style);
  ctx.fillStyle = style.color;
  ctx.letterSpacing = style.spacing ?? '0px';
  ctx.textAlign = style.align ?? 'left';
  ctx.textBaseline = 'alphabetic';
  ctx.fillText(text, x, y);
  ctx.letterSpacing = '0px';
  ctx.textAlign = 'left';
}

export function measure(ctx, text, style) {
  ctx.font = font(style);
  ctx.letterSpacing = style.spacing ?? '0px';
  const width = ctx.measureText(text).width;
  ctx.letterSpacing = '0px';
  return width;
}

/** Breaks text into at most maxLines lines that fit maxWidth, the last one ellipsised. */
export function wrapText(ctx, text, maxWidth, maxLines, style) {
  ctx.font = font(style);
  const words = text.split(/\s+/).filter(Boolean);
  const lines = [];
  let line = '';
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (ctx.measureText(candidate).width <= maxWidth || !line) {
      line = candidate;
    } else {
      lines.push(line);
      line = word;
    }
  }
  if (line) lines.push(line);
  if (lines.length > maxLines) {
    // The last line takes as much of the remainder as fits, cut mid-word if need be.
    let last = lines.slice(maxLines - 1).join(' ');
    lines.length = maxLines - 1;
    while (last.length > 1 && ctx.measureText(`${last}…`).width > maxWidth) last = last.slice(0, -1);
    lines.push(`${last.trimEnd()}…`);
  }
  return lines.map((entry) => {
    let fitted = entry;
    while (fitted.length > 1 && ctx.measureText(fitted).width > maxWidth) fitted = `${fitted.slice(0, -2)}…`;
    return fitted;
  });
}

/**
 * The sparkle of glitter filament over a rounded box: specks of varying size and brightness,
 * most of them bright and a few dark so it shows on light colours too. The positions come from
 * a seeded generator, so a card renders the same picture every time.
 */
export function drawGlitter(ctx, box, radius, seed = 1) {
  let state = seed >>> 0;
  const random = () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  ctx.save();
  roundedRect(ctx, box.x, box.y, box.width, box.height, radius);
  ctx.clip();
  const count = Math.round((box.width * box.height) / 120);
  for (let i = 0; i < count; i += 1) {
    const x = box.x + random() * box.width;
    const y = box.y + random() * box.height;
    const r = 0.4 + random() * 0.8;
    ctx.fillStyle = i % 6 === 5 ? `rgba(0, 0, 0, ${0.15 + random() * 0.15})` : `rgba(255, 255, 255, ${0.25 + random() * 0.6})`;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

export function roundedRect(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + width - r, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + r);
  ctx.lineTo(x + width, y + height - r);
  ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  ctx.lineTo(x + r, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}
