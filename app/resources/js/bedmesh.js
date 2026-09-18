/* Bed mesh helpers shared by the 3D view, the value grid and the legend. Pure, so node can run them. */

// Flat is emerald, at the tolerance and beyond it is red, amber in between: the app's status colours.
export const RAMP = [
  [16, 185, 129],
  [251, 191, 36],
  [239, 68, 68],
];

/** Min, max and mean over the probed points; null when the mesh has no values. */
export function meshStats(mesh) {
  const values = mesh.z.flat().filter((value) => value != null);
  if (!values.length) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  return { min, max, mean, range: max - min, count: values.length };
}

/** Colour for a height relative to the mean: how far it is from flat, as [r, g, b]. */
export function deviationColor(delta, tolerance) {
  const t = Math.min(Math.abs(delta) / Math.max(tolerance, 1e-6), 1) * (RAMP.length - 1);
  const index = Math.min(Math.floor(t), RAMP.length - 2);
  const mix = t - index;
  return RAMP[index].map((channel, axis) => Math.round(channel + (RAMP[index + 1][axis] - channel) * mix));
}

export function cssColor([r, g, b], alpha = 1) {
  return alpha === 1 ? `rgb(${r} ${g} ${b})` : `rgb(${r} ${g} ${b} / ${alpha})`;
}

export function formatMm(value, digits = 3) {
  if (value == null) return '–';
  return `${value < 0 ? '−' : '+'}${Math.abs(value).toFixed(digits)}`;
}

/**
 * Probe positions in mm: what the report said, otherwise spread over the bed area
 * (the mesh covers the whole bed on most printers) or over a unit square.
 */
export function meshPositions(mesh, area) {
  const spread = (low, size, count) => Array.from({ length: count }, (_, index) => low + (size * index) / Math.max(count - 1, 1));
  return {
    x: mesh.x ?? spread(area?.minX ?? 0, area?.sizeX ?? 1, mesh.cols),
    y: mesh.y ?? spread(area?.minY ?? 0, area?.sizeY ?? 1, mesh.rows),
  };
}
