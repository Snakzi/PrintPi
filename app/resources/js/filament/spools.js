/**
 * Pure helpers around spools: what is left, how it is labelled and whether a
 * file fits the loaded spool. Shared by the filament page, the widget and the
 * print start check.
 */

/**
 * A name that is free among the spools: the base name for the first spool of a
 * product, "#2", "#3" … for every further one, counting the ones already named
 * that way. `except` leaves the spool being edited out of the count.
 */
export function uniqueSpoolName(base, spools, except = null) {
  const pattern = new RegExp(`^${base.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?: #\\d+)?$`);
  const taken = spools.filter((spool) => spool.id !== except && pattern.test(spool.name)).length;
  return taken === 0 ? base : `${base} #${taken + 1}`;
}

/** The finishes a spool can have, as the form offers them; the ids are what the API accepts. */
export const FINISHES = [{ id: 'glitter', label: 'Glitter' }];

export function finishLabel(finish) {
  return FINISHES.find((entry) => entry.id === finish)?.label ?? null;
}

/** Vendor, material and finish as one muted line, whichever of them are known. */
export function spoolDetail(spool) {
  return [spool.vendor, spool.material, finishLabel(spool.finish)].filter(Boolean).join(' · ');
}

/** What is left of the spool as 0..1 of its net weight. */
export function remainingFraction(spool) {
  if (!spool || !spool.weight) return 0;
  return Math.min(1, Math.max(0, spool.remaining / spool.weight));
}

/** The bar colour for a fraction: green while plenty is left, amber below a quarter, red below a tenth. */
export function remainingTone(fraction) {
  if (fraction <= 0.1) return 'red';
  if (fraction <= 0.25) return 'amber';
  return 'emerald';
}

/** Grams of filament along a length of it, from the spool's diameter and density. */
export function gramsFor(spool, millimetres) {
  if (millimetres == null || !spool?.diameter || !spool?.density) return null;
  const section = Math.PI * (spool.diameter / 2) ** 2;
  return (millimetres * section * spool.density) / 1000;
}

/** The length of a mass of the spool's filament in millimetres, the inverse of gramsFor(). */
export function millimetresFor(spool, grams) {
  if (grams == null || !spool?.diameter || !spool?.density) return null;
  const section = Math.PI * (spool.diameter / 2) ** 2;
  return (grams * 1000) / (section * spool.density);
}

/** What a file needs in grams: the slicer's figure, else its length weighed with the spool. */
export function gramsNeeded(metadata, spool) {
  if (metadata?.filament_g != null) return metadata.filament_g;
  return gramsFor(spool, metadata?.filament_mm ?? null);
}

/** Materials compare loosely: "PLA" matches "pla", "PLA+" and "PLA Silk". */
export function materialMatches(fileType, spoolMaterial) {
  if (!fileType || !spoolMaterial) return true;
  const normalise = (value) => value.toUpperCase().replace(/[^A-Z0-9]/g, '');
  const a = normalise(fileType);
  const b = normalise(spoolMaterial);
  return a === b || a.startsWith(b) || b.startsWith(a);
}

/**
 * Why a file does not fit a spool, in a few words each: a material the file was
 * not sliced for, or less filament than it needs. Empty when it fits or when the
 * file's needs are unknown.
 */
export function printIssues(metadata, spool) {
  if (!spool || !metadata) return [];
  const issues = [];
  if (!materialMatches(metadata.filament_type, spool.material)) issues.push(`Sliced for ${metadata.filament_type}`);
  const needed = gramsNeeded(metadata, spool);
  if (needed != null && needed > spool.remaining) issues.push(`Needs ${Math.round(needed)} g, ${Math.round(spool.remaining)} g left`);
  return issues;
}
