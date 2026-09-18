import assert from 'node:assert/strict';
import { test } from 'node:test';
import { boxMatrices, extrusionBoxes, hiddenFeatures, layerHeights, mergeRuns } from './extrusionBoxes.js';
import { featureIndex } from './features.js';
import { parseGcode } from './parse.js';

const OUTER = featureIndex('External perimeter');
const INFILL = featureIndex('Internal infill');

function model(segments, { layerZ = [0.2], layerEnds = [segments.length], features = null } = {}) {
  return {
    extrusions: {
      count: segments.length,
      positions: Float32Array.from(segments.flat()),
      features: features ? Uint8Array.from(features) : null,
    },
    layerZ: Float32Array.from(layerZ),
    layerExtrusionEnd: Uint32Array.from(layerEnds),
  };
}

test('layer heights come from the Z steps, the first from the bed', () => {
  assert.deepEqual(Array.from(layerHeights(Float32Array.of(0.2, 0.4, 0.7))).map((h) => h.toFixed(2)), ['0.20', '0.20', '0.30']);
  assert.deepEqual(Array.from(layerHeights(Float32Array.of(5, 5.01))).map((h) => h.toFixed(2)), ['1.00', '0.05']);
});

test('joined segments that barely turn become one run', () => {
  const runs = mergeRuns(
    model([
      [0, 0, 0.2, 1, 0, 0.2],
      [1, 0, 0.2, 2, 0.05, 0.2],
      [2, 0.05, 0.2, 3, 0.1, 0.2],
    ]),
    12,
  );
  assert.deepEqual(Array.from(runs).map((v) => Number(v.toFixed(3))), [0, 0, 0.2, 3, 0.1, 0.2]);
});

test('a sharp corner, a gap, a new layer and a hidden feature end the run', () => {
  const runs = mergeRuns(
    model(
      [
        [0, 0, 0.2, 1, 0, 0.2],
        [1, 0, 0.2, 1, 1, 0.2], // 90° corner
        [1, 1, 0.2, 2, 1, 0.2],
        [5, 5, 0.2, 6, 5, 0.2], // not joined
        [6, 5, 0.2, 7, 5, 0.2],
        [0, 0, 0.4, 1, 0, 0.4], // next layer
        [1, 0, 0.4, 2, 0, 0.4],
      ],
      { layerZ: [0.2, 0.4], layerEnds: [5, 7], features: [OUTER, OUTER, OUTER, OUTER, INFILL, OUTER, OUTER] },
    ),
    12,
  );
  const starts = [];
  for (let i = 0; i < runs.length; i += 6) starts.push([runs[i], runs[i + 1], runs[i + 3], runs[i + 4], runs[i + 5]]);
  assert.deepEqual(
    starts.map((r) => r.map((v) => Number(v.toFixed(2)))),
    [
      [0, 0, 1, 0, 0.2],
      [1, 0, 1, 1, 0.2],
      [1, 1, 2, 1, 0.2],
      [5, 5, 6, 5, 0.2],
      [0, 0, 2, 0, 0.2],
    ],
  );
});

test('a long straight wall is cut into several boxes', () => {
  const segments = [];
  for (let x = 0; x < 30; x += 1) segments.push([x, 0, 0.2, x + 1, 0, 0.2]);
  const runs = mergeRuns(model(segments), 12);
  assert.equal(runs.length / 6, 4);
});

test('box matrices place a unit cube along the run with the layer as top face', () => {
  const m = boxMatrices(Float32Array.of(0, 0, 0.4, 4, 0, 0.2), 0.5);
  assert.equal(m.length, 16);
  assert.deepEqual(Array.from(m.slice(0, 2)), [4.5, 0]); // x axis: length plus width
  assert.deepEqual(Array.from(m.slice(4, 6)), [-0, 0.5]); // y axis: the width
  assert.equal(m[10].toFixed(2), '0.30'); // z axis: the layer height plus the sink into the layer below
  assert.deepEqual(Array.from(m.slice(12, 16)).map((v) => Number(v.toFixed(3))), [2, 0, 0.25, 1]); // top face at 0.4

  const turned = boxMatrices(Float32Array.of(0, 0, 0.2, 0, 3, 0.2), 0.5);
  assert.deepEqual(Array.from(turned.slice(0, 2)).map((v) => Number(v.toFixed(3))), [0, 3.5]);
});

test('untyped extrusions are hidden only when the slicer typed the rest', () => {
  const typed = parseGcode('G1 X0 Y-4 Z0.2 E0\nG1 X100 Y-4 E10\n;TYPE:External perimeter\nG1 X10 Y10\nG1 X20 Y10 E12\n');
  assert.ok(hiddenFeatures(typed).has(featureIndex('other')));
  const boxes = extrusionBoxes(typed);
  assert.equal(boxes.count, 1);
  assert.deepEqual(boxes.bounds.min.slice(0, 2), [10, 10]);
  assert.deepEqual(boxes.bounds.max.map((v) => Number(v.toFixed(2))), [20, 10, 0.2]);

  const untyped = parseGcode('G1 X0 Y0 Z0.2 E0\nG1 X10 Y0 E10\n');
  assert.ok(!hiddenFeatures(untyped).has(featureIndex('other')));
  assert.equal(extrusionBoxes(untyped).count, 1);
});

test('the budget widens the merge angle before it drops the inner walls', () => {
  const gcode = [';TYPE:External perimeter', 'G1 X0 Y0 Z0.2 E0'];
  for (let i = 1; i <= 360; i += 1) gcode.push(`G1 X${(10 * Math.cos((i * Math.PI) / 180)).toFixed(3)} Y${(10 * Math.sin((i * Math.PI) / 180)).toFixed(3)} E${i}`);
  const parsed = parseGcode(gcode.join('\n'));
  const fine = extrusionBoxes(parsed, { budget: 1000 });
  const coarse = extrusionBoxes(parsed, { budget: 12 });
  assert.ok(fine.count > 20 && coarse.count <= 12, `${fine.count} fine, ${coarse.count} coarse`);
  assert.equal(fine.matrices.length, fine.count * 16);
});
