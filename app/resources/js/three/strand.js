/*
 * The cross-section every extrusion is drawn with: a stadium, flat on top and
 * bottom with round sides, so a wall shades smoothly from its top edge down
 * instead of showing the hard edges of a box. Unit size along X, Y and Z; the
 * instance matrix stretches it to the run's length, the line width and the
 * layer height.
 */

import { BufferAttribute, BufferGeometry } from 'three';

const ASPECT = 0.45 / 0.2; // width over height of a typical line, which sets the share of the flat top
const SIDE_STEPS = 4;

/**
 * The closed profile in the YZ plane as [y, z, ny, nz] rows, counter-clockwise seen from +X:
 * up the right side, across the top, down the left side and back across the bottom.
 */
export function strandProfile(aspect = ASPECT, steps = SIDE_STEPS) {
  const ry = 0.5 / aspect; // the round side is a half circle of the layer height, squeezed into unit width
  const rz = 0.5;
  const flat = 0.5 - ry;
  const rows = [];
  const arc = (centerY, from, to) => {
    for (let step = 0; step <= steps; step += 1) {
      const angle = from + ((to - from) * step) / steps;
      const ny = Math.cos(angle) / ry;
      const nz = Math.sin(angle) / rz;
      const length = Math.hypot(ny, nz);
      rows.push([centerY + ry * Math.cos(angle), rz * Math.sin(angle), ny / length, nz / length]);
    }
  };
  arc(flat, -Math.PI / 2, Math.PI / 2);
  arc(-flat, Math.PI / 2, (3 * Math.PI) / 2);
  return rows;
}

/** The profile extruded from x -0.5 to 0.5 with flat end caps, normals smooth around the sides. */
export function strandGeometry(profile = strandProfile()) {
  const ring = profile.length;
  const positions = [];
  const normals = [];
  const indices = [];

  for (const x of [-0.5, 0.5]) {
    for (const [y, z, ny, nz] of profile) {
      positions.push(x, y, z);
      normals.push(0, ny, nz);
    }
  }
  for (let i = 0; i < ring; i += 1) {
    const a = i;
    const b = (i + 1) % ring;
    const c = ring + b;
    const d = ring + a;
    indices.push(a, b, c, a, c, d);
  }

  for (const [x, nx] of [
    [0.5, 1],
    [-0.5, -1],
  ]) {
    const start = positions.length / 3;
    for (const [y, z] of profile) {
      positions.push(x, y, z);
      normals.push(nx, 0, 0);
    }
    for (let i = 1; i < ring - 1; i += 1) {
      if (nx > 0) indices.push(start, start + i, start + i + 1);
      else indices.push(start, start + i + 1, start + i);
    }
  }

  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(Float32Array.from(positions), 3));
  geometry.setAttribute('normal', new BufferAttribute(Float32Array.from(normals), 3));
  geometry.setIndex(indices);
  return geometry;
}
