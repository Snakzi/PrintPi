/**
 * Extrusion feature types the 3D preview colors, in legend order. The palette
 * follows PrusaSlicer's G-code viewer so users recognize it.
 */
export const FEATURES = [
  { id: 'outer-wall', label: 'Outer wall', color: '#ff7d38' },
  { id: 'inner-wall', label: 'Inner wall', color: '#ffe64d' },
  { id: 'infill', label: 'Infill', color: '#b03029' },
  { id: 'solid-infill', label: 'Solid infill', color: '#9654cc' },
  { id: 'top-surface', label: 'Top surface', color: '#f04040' },
  { id: 'bridge', label: 'Bridge', color: '#4d80ba' },
  { id: 'skirt', label: 'Skirt / brim', color: '#00876e' },
  { id: 'support', label: 'Support', color: '#22c55e' },
  { id: 'gap-fill', label: 'Gap fill', color: '#f4f4f5' },
  { id: 'ironing', label: 'Ironing', color: '#ff8c69' },
  { id: 'wipe-tower', label: 'Wipe tower', color: '#b3e3ab' },
  { id: 'other', label: 'Other', color: '#a1a1aa' },
];

export const TRAVEL_COLOR = '#71717a';

export const OTHER_FEATURE = FEATURES.findIndex((feature) => feature.id === 'other');

const INDEX = Object.fromEntries(FEATURES.map((feature, index) => [feature.id, index]));

/** ;TYPE: names of PrusaSlicer, OrcaSlicer, Bambu Studio, Cura and Simplify3D. */
const ALIASES = {
  'external perimeter': 'outer-wall',
  'overhang perimeter': 'outer-wall',
  'outer wall': 'outer-wall',
  'overhang wall': 'outer-wall',
  'wall-outer': 'outer-wall',
  'outer perimeter': 'outer-wall',
  perimeter: 'inner-wall',
  'inner wall': 'inner-wall',
  'wall-inner': 'inner-wall',
  'inner perimeter': 'inner-wall',
  'internal infill': 'infill',
  'sparse infill': 'infill',
  fill: 'infill',
  infill: 'infill',
  'solid infill': 'solid-infill',
  'internal solid infill': 'solid-infill',
  'bottom surface': 'solid-infill',
  skin: 'solid-infill',
  'solid layer': 'solid-infill',
  'top solid infill': 'top-surface',
  'top surface': 'top-surface',
  'bridge infill': 'bridge',
  'internal bridge infill': 'bridge',
  'internal bridge': 'bridge',
  bridge: 'bridge',
  'skirt/brim': 'skirt',
  skirt: 'skirt',
  brim: 'skirt',
  'support material': 'support',
  'support material interface': 'support',
  support: 'support',
  'support interface': 'support',
  'support-interface': 'support',
  'support transition': 'support',
  'gap fill': 'gap-fill',
  'gap infill': 'gap-fill',
  ironing: 'ironing',
  'wipe tower': 'wipe-tower',
  'prime tower': 'wipe-tower',
  'prime-tower': 'wipe-tower',
};

export function featureIndex(typeName) {
  return INDEX[ALIASES[typeName.trim().toLowerCase()] ?? 'other'];
}
