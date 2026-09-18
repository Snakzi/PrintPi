import assert from 'node:assert/strict';
import { test } from 'node:test';
import { strandGeometry, strandProfile } from './strand.js';

test('the profile is a unit stadium with unit normals, flat on top and bottom', () => {
  const profile = strandProfile();
  const ys = profile.map(([y]) => y);
  const zs = profile.map(([, z]) => z);
  assert.equal(Math.min(...ys).toFixed(3), '-0.500');
  assert.equal(Math.max(...ys).toFixed(3), '0.500');
  assert.equal(Math.min(...zs).toFixed(3), '-0.500');
  assert.equal(Math.max(...zs).toFixed(3), '0.500');
  for (const [, , ny, nz] of profile) assert.equal(Math.hypot(ny, nz).toFixed(6), '1.000000');
  const top = profile.filter(([, z, , nz]) => z > 0.499 && nz > 0.999);
  assert.equal(top.length, 2, 'the two ends of the flat top face straight up');
});

test('every face of the strand winds outward, against its own normals', () => {
  const geometry = strandGeometry();
  const position = geometry.getAttribute('position');
  const normal = geometry.getAttribute('normal');
  const index = geometry.getIndex();
  const vertex = (i) => [position.getX(i), position.getY(i), position.getZ(i)];
  for (let t = 0; t < index.count; t += 3) {
    const [a, b, c] = [index.getX(t), index.getX(t + 1), index.getX(t + 2)];
    const [ax, ay, az] = vertex(a);
    const [bx, by, bz] = vertex(b);
    const [cx, cy, cz] = vertex(c);
    const e1 = [bx - ax, by - ay, bz - az];
    const e2 = [cx - ax, cy - ay, cz - az];
    const face = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
    const dot = face[0] * normal.getX(a) + face[1] * normal.getY(a) + face[2] * normal.getZ(a);
    assert.ok(dot > 0, `triangle ${t / 3} faces inward`);
  }
});
