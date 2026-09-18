import { FEATURES } from './features.js';

/**
 * Turns the extrusion segments of a parsed model into one box per stretch of
 * path, as instance matrices for a unit cube: a printed line with the layer
 * height and the extrusion width, so lights and shadows work on it. Runs of
 * nearly collinear segments become one box, and sparse infill is left out
 * because it is hidden inside the part, so a long print stays drawable.
 */

const feature = (id) => FEATURES.findIndex((entry) => entry.id === id);
const INFILL = feature('infill');
const INNER_WALL = feature('inner-wall');
const OTHER = feature('other');
// Ever coarser merging, then the inner walls go too; the outer wall covers them anyway.
const PASSES = [
  { maxAngle: 6, dropInnerWalls: false },
  { maxAngle: 12, dropInnerWalls: false },
  { maxAngle: 25, dropInnerWalls: false },
  { maxAngle: 45, dropInnerWalls: false },
  { maxAngle: 45, dropInnerWalls: true },
];
const MAX_RUN = 8; // mm of path one box may stand in for
const MIN_HEIGHT = 0.05;
const MAX_HEIGHT = 1;
// Each strand reaches this far into the layer below, so only its upper, lit side shows and
// the layers read as one smooth surface rather than as ribs with dark undersides.
const SINK = 1.5;

export const DEFAULT_WIDTH = 0.45;
export const DEFAULT_BUDGET = 300000;

/** Height of every layer from the layer Z values, the first one measured from the bed. */
export function layerHeights(layerZ) {
  const heights = new Float32Array(layerZ.length);
  for (let index = 0; index < layerZ.length; index += 1) {
    const height = layerZ[index] - (index ? layerZ[index - 1] : 0);
    heights[index] = Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, height));
  }
  return heights;
}

/**
 * Feature types left out of the drawing. Untyped extrusions are the purge line and the
 * like when the slicer types the rest, else they are the whole model.
 */
export function hiddenFeatures(model, { dropInnerWalls = false } = {}) {
  const hidden = new Set([INFILL]);
  if (dropInnerWalls) hidden.add(INNER_WALL);
  const used = model.featuresUsed;
  if (used && Array.from(used).some((flag, index) => flag && index !== OTHER)) hidden.add(OTHER);
  return hidden;
}

/**
 * Merges the drawable segments into runs: consecutive segments that join end to start and
 * turn less than `maxAngle` degrees away from the run's first direction. Returns flat
 * [x1, y1, z, x2, y2, height] per run.
 */
export function mergeRuns(model, maxAngle, hidden = hiddenFeatures(model)) {
  const { extrusions, layerZ, layerExtrusionEnd } = model;
  const heights = layerZ.length ? layerHeights(layerZ) : Float32Array.of(0.2);
  const cosLimit = Math.cos((maxAngle * Math.PI) / 180);
  const positions = extrusions.positions;
  const features = extrusions.features;
  const runs = [];

  let layer = 0;
  let first = -1; // index of the run's first segment
  let firstDx = 0;
  let firstDy = 0;
  let runLength = 0;

  const flush = (last) => {
    if (first < 0) return;
    const start = first * 6;
    const end = last * 6;
    runs.push(positions[start], positions[start + 1], positions[start + 2], positions[end + 3], positions[end + 4], heights[Math.min(layer, heights.length - 1)]);
    first = -1;
  };

  for (let index = 0; index < extrusions.count; index += 1) {
    while (layer < layerExtrusionEnd.length - 1 && index >= layerExtrusionEnd[layer]) {
      flush(index - 1);
      layer += 1;
    }
    const offset = index * 6;
    const dx = positions[offset + 3] - positions[offset];
    const dy = positions[offset + 4] - positions[offset + 1];
    const length = Math.hypot(dx, dy);
    if ((features && hidden.has(features[index])) || length === 0) {
      flush(index - 1);
      continue;
    }

    if (first >= 0) {
      const previous = (index - 1) * 6;
      const joined = positions[previous + 3] === positions[offset] && positions[previous + 4] === positions[offset + 1] && positions[previous + 5] === positions[offset + 2];
      const cosine = (firstDx * dx + firstDy * dy) / length;
      if (joined && cosine >= cosLimit && runLength + length <= MAX_RUN) {
        runLength += length;
        continue;
      }
      flush(index - 1);
    }
    first = index;
    firstDx = dx / length;
    firstDy = dy / length;
    runLength = length;
  }
  flush(extrusions.count - 1);
  return Float32Array.from(runs);
}

/**
 * Column-major 4x4 matrices placing a unit cube on every run: rotated along the path,
 * stretched to its length plus the width so neighbouring boxes overlap at the joints,
 * and sunk by SINK layer heights so the run's Z is the top face.
 */
export function boxMatrices(runs, width = DEFAULT_WIDTH) {
  const count = runs.length / 6;
  const matrices = new Float32Array(count * 16);
  for (let index = 0; index < count; index += 1) {
    const o = index * 6;
    const dx = runs[o + 3] - runs[o];
    const dy = runs[o + 4] - runs[o + 1];
    const length = Math.hypot(dx, dy);
    const cos = dx / length;
    const sin = dy / length;
    const sx = length + width;
    const height = runs[o + 5];
    const m = index * 16;
    matrices[m] = cos * sx;
    matrices[m + 1] = sin * sx;
    matrices[m + 4] = -sin * width;
    matrices[m + 5] = cos * width;
    matrices[m + 10] = height * SINK;
    matrices[m + 12] = (runs[o] + runs[o + 3]) / 2;
    matrices[m + 13] = (runs[o + 1] + runs[o + 4]) / 2;
    matrices[m + 14] = runs[o + 2] - (height * SINK) / 2;
    matrices[m + 15] = 1;
  }
  return matrices;
}

/** The extent of the runs as { min: [x, y, z], max: [x, y, z] }, z from the bed to the top face. */
export function runBounds(runs) {
  const min = [Infinity, Infinity, 0];
  const max = [-Infinity, -Infinity, -Infinity];
  for (let o = 0; o < runs.length; o += 6) {
    min[0] = Math.min(min[0], runs[o], runs[o + 3]);
    min[1] = Math.min(min[1], runs[o + 1], runs[o + 4]);
    max[0] = Math.max(max[0], runs[o], runs[o + 3]);
    max[1] = Math.max(max[1], runs[o + 1], runs[o + 4]);
    max[2] = Math.max(max[2], runs[o + 2]);
  }
  return runs.length ? { min, max } : { min: [0, 0, 0], max: [0, 0, 0] };
}

/**
 * Boxes for the whole model within `budget` instances: the merge angle is widened
 * step by step until the count fits, which only coarsens curves a little.
 */
export function extrusionBoxes(model, { width = DEFAULT_WIDTH, budget = DEFAULT_BUDGET } = {}) {
  let runs = null;
  for (const pass of PASSES) {
    runs = mergeRuns(model, pass.maxAngle, hiddenFeatures(model, pass));
    if (runs.length / 6 <= budget) break;
  }
  return { count: runs.length / 6, matrices: boxMatrices(runs, width), bounds: runBounds(runs) };
}
