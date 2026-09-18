import { FEATURES, OTHER_FEATURE, featureIndex } from './features.js';

const CHAR_TAB = 9;
const CHAR_SPACE = 32;
const CHAR_STAR = 42;
const CHAR_SEMICOLON = 59;
const CHAR_G = 71;
const CHAR_M = 77;
const CHAR_N = 78;

/** Arc moves (G2/G3) are flattened into chords of roughly this length in mm. */
const ARC_CHORD = 0.5;
const LAYER_EPSILON = 0.001;

/**
 * Line segments as a flat xyz-xyz float buffer that doubles when full. Each
 * segment remembers the 1-based file line it came from, so a running print's
 * position in the file maps back to the drawn geometry.
 */
class Segments {
  constructor(withFeatures) {
    this.capacity = 1 << 16;
    this.positions = new Float32Array(this.capacity * 6);
    this.features = withFeatures ? new Uint8Array(this.capacity) : null;
    this.lines = new Uint32Array(this.capacity);
    this.count = 0;
  }

  push(x1, y1, z1, x2, y2, z2, feature, line) {
    if (this.count === this.capacity) this.grow();
    const o = this.count * 6;
    const p = this.positions;
    p[o] = x1;
    p[o + 1] = y1;
    p[o + 2] = z1;
    p[o + 3] = x2;
    p[o + 4] = y2;
    p[o + 5] = z2;
    if (this.features) this.features[this.count] = feature;
    this.lines[this.count] = line;
    this.count += 1;
  }

  grow() {
    this.capacity *= 2;
    const positions = new Float32Array(this.capacity * 6);
    positions.set(this.positions);
    this.positions = positions;
    if (this.features) {
      const features = new Uint8Array(this.capacity);
      features.set(this.features);
      this.features = features;
    }
    const lines = new Uint32Array(this.capacity);
    lines.set(this.lines);
    this.lines = lines;
  }

  finish() {
    return {
      count: this.count,
      positions: this.positions.slice(0, this.count * 6),
      features: this.features ? this.features.slice(0, this.count) : null,
      lines: this.lines.slice(0, this.count),
    };
  }
}

/** Number of segments whose source line is at or before `line` (lines ascend with the file). */
export function segmentsUpToLine(lines, line) {
  let low = 0;
  let high = lines.length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (lines[mid] <= line) low = mid + 1;
    else high = mid;
  }
  return low;
}

/**
 * Turns Marlin-flavoured G-code into line segments for the 3D preview.
 *
 * Extrusions carry the slicer's feature type, travels are kept separately so
 * the viewer can toggle them. Layers come from ;LAYER_CHANGE / ;LAYER: comments
 * when the slicer writes them, otherwise from the Z of each extrusion.
 */
export function parseGcode(text) {
  const extrusions = new Segments(true);
  const travels = new Segments(false);
  const layerZ = [];
  const layerExtrusionEnd = [];
  const layerTravelEnd = [];
  const featuresUsed = new Uint8Array(FEATURES.length);
  const bounds = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };

  let x = 0;
  let y = 0;
  let z = 0;
  let e = 0;
  let absolute = true;
  let absoluteE = true;
  let feature = OTHER_FEATURE;
  let usesLayerMarkers = false;
  let layerPending = false;
  let lineNumber = 0;

  // Parameters of the current command; NaN means absent.
  let px;
  let py;
  let pz;
  let pe;
  let pi;
  let pj;
  let pr;

  // Travels after a layer's last extrusion belong to the next layer.
  let travelsAtLastExtrusion = 0;

  function closeLayer(travelEnd) {
    const last = layerZ.length - 1;
    layerExtrusionEnd[last] = extrusions.count;
    layerTravelEnd[last] = travelEnd;
  }

  function beginLayer(layerHeight) {
    if (layerZ.length) closeLayer(travelsAtLastExtrusion);
    layerZ.push(layerHeight);
    layerExtrusionEnd.push(extrusions.count);
    layerTravelEnd.push(travels.count);
  }

  function extrude(x1, y1, z1, x2, y2, z2) {
    const currentZ = layerZ.length ? layerZ[layerZ.length - 1] : NaN;
    const newLayer = usesLayerMarkers
      ? layerPending && Math.abs(z2 - currentZ) > LAYER_EPSILON
      : z2 > currentZ + LAYER_EPSILON;
    if (layerZ.length === 0 || newLayer) beginLayer(z2);
    layerPending = false;

    extrusions.push(x1, y1, z1, x2, y2, z2, feature, lineNumber);
    travelsAtLastExtrusion = travels.count;
    featuresUsed[feature] = 1;
    if (x2 < bounds.min[0]) bounds.min[0] = x2;
    if (y2 < bounds.min[1]) bounds.min[1] = y2;
    if (z2 < bounds.min[2]) bounds.min[2] = z2;
    if (x2 > bounds.max[0]) bounds.max[0] = x2;
    if (y2 > bounds.max[1]) bounds.max[1] = y2;
    if (z2 > bounds.max[2]) bounds.max[2] = z2;
  }

  function segment(x1, y1, z1, x2, y2, z2, extruding) {
    if (extruding) {
      extrude(x1, y1, z1, x2, y2, z2);
    } else {
      travels.push(x1, y1, z1, x2, y2, z2, 0, lineNumber);
    }
  }

  function target() {
    const nx = Number.isNaN(px) ? x : absolute ? px : x + px;
    const ny = Number.isNaN(py) ? y : absolute ? py : y + py;
    const nz = Number.isNaN(pz) ? z : absolute ? pz : z + pz;
    const ne = Number.isNaN(pe) ? e : absoluteE ? pe : e + pe;
    return [nx, ny, nz, ne];
  }

  function linearMove() {
    const [nx, ny, nz, ne] = target();
    if (nx !== x || ny !== y || nz !== z) {
      segment(x, y, z, nx, ny, nz, ne > e);
    }
    x = nx;
    y = ny;
    z = nz;
    e = ne;
  }

  function arcMove(clockwise) {
    const [nx, ny, nz, ne] = target();
    let cx;
    let cy;
    if (!Number.isNaN(pi) || !Number.isNaN(pj)) {
      cx = x + (Number.isNaN(pi) ? 0 : pi);
      cy = y + (Number.isNaN(pj) ? 0 : pj);
    } else if (!Number.isNaN(pr)) {
      const dx = nx - x;
      const dy = ny - y;
      const chord = Math.hypot(dx, dy);
      if (chord === 0) return linearMove();
      const radius = Math.abs(pr);
      const height = Math.sqrt(Math.max(0, radius * radius - (chord * chord) / 4));
      // Positive R takes the short arc: its center is left of the chord for
      // counter-clockwise arcs, right for clockwise ones.
      const side = (clockwise ? -1 : 1) * (pr < 0 ? -1 : 1);
      cx = x + dx / 2 + (side * height * -dy) / chord;
      cy = y + dy / 2 + (side * height * dx) / chord;
    } else {
      return linearMove();
    }

    const radius = Math.hypot(x - cx, y - cy);
    const startAngle = Math.atan2(y - cy, x - cx);
    let sweep = Math.atan2(ny - cy, nx - cx) - startAngle;
    if (clockwise && sweep >= 0) sweep -= Math.PI * 2;
    if (!clockwise && sweep <= 0) sweep += Math.PI * 2;

    const steps = Math.max(2, Math.min(128, Math.ceil((Math.abs(sweep) * radius) / ARC_CHORD)));
    const extruding = ne > e;
    let lx = x;
    let ly = y;
    let lz = z;
    for (let step = 1; step <= steps; step += 1) {
      const t = step / steps;
      const angle = startAngle + sweep * t;
      const sx = step === steps ? nx : cx + radius * Math.cos(angle);
      const sy = step === steps ? ny : cy + radius * Math.sin(angle);
      const sz = z + (nz - z) * t;
      segment(lx, ly, lz, sx, sy, sz, extruding);
      lx = sx;
      ly = sy;
      lz = sz;
    }
    x = nx;
    y = ny;
    z = nz;
    e = ne;
    return undefined;
  }

  function comment(body) {
    const trimmed = body.trim();
    const upper = trimmed.toUpperCase();
    if (upper.startsWith('TYPE:')) {
      feature = featureIndex(trimmed.slice(5));
    } else if (upper.startsWith('FEATURE:')) {
      feature = featureIndex(trimmed.slice(8));
    } else if (upper.startsWith('FEATURE ')) {
      feature = featureIndex(trimmed.slice(8));
    } else if (upper.startsWith('LAYER_CHANGE') || upper.startsWith('LAYER:') || upper.startsWith('LAYER ')) {
      usesLayerMarkers = true;
      layerPending = true;
    }
  }

  function readParameters(line, from, to) {
    px = py = pz = pe = pi = pj = pr = NaN;
    let i = from;
    while (i < to) {
      const code = line.charCodeAt(i);
      if (code === CHAR_SPACE || code === CHAR_TAB) {
        i += 1;
        continue;
      }
      if (code === CHAR_STAR) break;
      const letter = code | 32;
      i += 1;
      const numberStart = i;
      while (i < to) {
        const c = line.charCodeAt(i);
        if (c === CHAR_SPACE || c === CHAR_TAB || c === CHAR_STAR) break;
        i += 1;
      }
      const value = parseFloat(line.slice(numberStart, i));
      if (letter === 120) px = value;
      else if (letter === 121) py = value;
      else if (letter === 122) pz = value;
      else if (letter === 101) pe = value;
      else if (letter === 105) pi = value;
      else if (letter === 106) pj = value;
      else if (letter === 114) pr = value;
    }
  }

  function command(line) {
    let i = 0;
    let end = line.length;
    while (i < end && (line.charCodeAt(i) === CHAR_SPACE || line.charCodeAt(i) === CHAR_TAB)) i += 1;
    if (i >= end) return;
    if (line.charCodeAt(i) === CHAR_SEMICOLON) {
      comment(line.slice(i + 1));
      return;
    }
    const semicolon = line.indexOf(';', i);
    if (semicolon !== -1) end = semicolon;

    if (line.charCodeAt(i) === CHAR_N) {
      i += 1;
      while (i < end && line.charCodeAt(i) !== CHAR_SPACE) i += 1;
      while (i < end && line.charCodeAt(i) === CHAR_SPACE) i += 1;
    }
    const letter = line.charCodeAt(i);
    if (letter !== CHAR_G && letter !== CHAR_M && (letter | 32) !== (CHAR_G | 32) && (letter | 32) !== (CHAR_M | 32)) return;
    i += 1;
    const numberStart = i;
    while (i < end && line.charCodeAt(i) !== CHAR_SPACE && line.charCodeAt(i) !== CHAR_TAB) i += 1;
    const number = parseInt(line.slice(numberStart, i), 10);
    if (Number.isNaN(number)) return;
    readParameters(line, i, end);

    if ((letter | 32) === (CHAR_G | 32)) {
      switch (number) {
        case 0:
        case 1:
          linearMove();
          break;
        case 2:
          arcMove(true);
          break;
        case 3:
          arcMove(false);
          break;
        case 28:
          if (Number.isNaN(px) && Number.isNaN(py) && Number.isNaN(pz)) {
            x = y = z = 0;
          } else {
            if (!Number.isNaN(px)) x = 0;
            if (!Number.isNaN(py)) y = 0;
            if (!Number.isNaN(pz)) z = 0;
          }
          break;
        case 90:
          absolute = true;
          absoluteE = true;
          break;
        case 91:
          absolute = false;
          absoluteE = false;
          break;
        case 92:
          if (!Number.isNaN(px)) x = px;
          if (!Number.isNaN(py)) y = py;
          if (!Number.isNaN(pz)) z = pz;
          if (!Number.isNaN(pe)) e = pe;
          break;
        default:
          break;
      }
    } else if (number === 82) {
      absoluteE = true;
    } else if (number === 83) {
      absoluteE = false;
    }
  }

  let start = 0;
  const length = text.length;
  while (start < length) {
    let end = text.indexOf('\n', start);
    if (end === -1) end = length;
    lineNumber += 1;
    if (end > start) command(text.substring(start, end));
    start = end + 1;
  }
  if (layerZ.length) closeLayer(travels.count);

  if (extrusions.count === 0) {
    bounds.min = [0, 0, 0];
    bounds.max = [0, 0, 0];
  }

  return {
    extrusions: extrusions.finish(),
    travels: travels.finish(),
    layerZ: Float32Array.from(layerZ),
    layerExtrusionEnd: Uint32Array.from(layerExtrusionEnd),
    layerTravelEnd: Uint32Array.from(layerTravelEnd),
    featuresUsed,
    bounds,
  };
}

/** The ArrayBuffers of a parse result, for a zero-copy postMessage. */
export function transferables(result) {
  const buffers = [
    result.extrusions.positions.buffer,
    result.extrusions.lines.buffer,
    result.travels.positions.buffer,
    result.travels.lines.buffer,
    result.layerZ.buffer,
    result.layerExtrusionEnd.buffer,
    result.layerTravelEnd.buffer,
    result.featuresUsed.buffer,
  ];
  if (result.extrusions.features) buffers.push(result.extrusions.features.buffer);
  return buffers;
}
