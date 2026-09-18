/**
 * The favicon with a progress ring around the logo. The logo is the page's own SVG icon drawn
 * onto a canvas, the ring an arc in the tone's colour over a dim track; `showRing` swaps the
 * icon links for one PNG data URL and `restoreFavicon` puts the original links back.
 */
const SIZE = 64;
const LOGO = 36;
const RADIUS = 28;
const STROKE = 5;
const TRACK = '#3f3f46';
const TONES = { emerald: '#34d399', sky: '#38bdf8', amber: '#fbbf24', red: '#f87171', zinc: '#a1a1aa' };

let originals = null;
let ringLink = null;
let logo = null;
let logoLoading = null;

function loadLogo() {
  if (logo) return Promise.resolve(logo);
  if (!logoLoading) {
    logoLoading = new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => {
        logo = image;
        resolve(image);
      };
      image.onerror = reject;
      image.src = '/favicon.svg';
    });
  }
  return logoLoading;
}

export function drawRing(image, fraction, tone) {
  const canvas = document.createElement('canvas');
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext('2d');
  const centre = SIZE / 2;
  const start = -Math.PI / 2;

  ctx.drawImage(image, centre - LOGO / 2, centre - LOGO / 2, LOGO, LOGO);
  ctx.lineWidth = STROKE;
  ctx.lineCap = 'round';
  ctx.strokeStyle = TRACK;
  ctx.beginPath();
  ctx.arc(centre, centre, RADIUS, 0, Math.PI * 2);
  ctx.stroke();
  if (fraction > 0) {
    ctx.strokeStyle = TONES[tone] ?? TONES.zinc;
    ctx.beginPath();
    ctx.arc(centre, centre, RADIUS, start, start + Math.PI * 2 * fraction);
    ctx.stroke();
  }
  return canvas.toDataURL('image/png');
}

export async function showRing(fraction, tone) {
  const image = await loadLogo();
  const url = drawRing(image, fraction, tone);
  if (!originals) {
    originals = Array.from(document.querySelectorAll('link[rel~="icon"]'));
    originals.forEach((link) => link.remove());
  }
  if (!ringLink) {
    ringLink = document.createElement('link');
    ringLink.rel = 'icon';
    ringLink.type = 'image/png';
    document.head.appendChild(ringLink);
  }
  ringLink.href = url;
}

export function restoreFavicon() {
  if (!originals) return;
  ringLink?.remove();
  ringLink = null;
  originals.forEach((link) => document.head.appendChild(link));
  originals = null;
}
