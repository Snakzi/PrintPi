import assert from 'node:assert/strict';
import { test } from 'node:test';
import { outcomeLabel, postcardStats } from './render.js';
import { wrapText } from '../canvas/draw.js';
import { formatCost, formatEnergy, formatFilament, formatLength, formatWeight, stripGcodeExtension } from '../format.js';

const finished = {
  name: 'Benchy (0.2mm, PLA).gcode',
  state: 'finished',
  progress: 1,
  elapsed: 3725,
  layers: 120,
  total_layers: 120,
  filament_g: 12.5,
  filament_mm: 4000,
  energy_wh: 42.5,
  slicer: 'PrusaSlicer 2.8.1+MacOS',
};

test('the outcome names finished, cancelled and failed prints', () => {
  assert.equal(outcomeLabel(finished), 'Finished');
  assert.equal(outcomeLabel({ ...finished, state: 'cancelled', progress: 0.4 }), 'Cancelled at 40 %');
  assert.equal(outcomeLabel({ ...finished, state: 'error', progress: 0.05 }), 'Failed at 5 %');
});

test('the figures cover time, layers, filament and energy with its cost', () => {
  const stats = postcardStats(finished, { energyPrice: 0.3, currency: '€' });
  assert.deepEqual(
    stats.map((stat) => [stat.label, stat.value, stat.note ?? null]),
    [
      ['Print time', '1 h 2 min', null],
      ['Layers', '120', null],
      ['Filament', '13 g', null],
      ['Energy', '43 Wh', '0.01 €'],
    ],
  );
});

test('a cancelled print shows how far it got and falls back to the slicer', () => {
  const stats = postcardStats({ ...finished, state: 'cancelled', progress: 0.4, layers: 48, energy_wh: null });
  assert.equal(stats[1].value, '48 / 120');
  assert.deepEqual(stats[3], { label: 'Slicer', value: 'PrusaSlicer' });
  assert.equal(postcardStats({ ...finished, energy_wh: null, slicer: null }).length, 3);
  assert.equal(postcardStats({ ...finished, energy_wh: 1500 })[3].note, null);
  assert.equal(postcardStats({ ...finished, filament_cost: 0.38 }, { currency: '€' })[2].note, '0.38 €');
});

test('formatters', () => {
  assert.equal(formatEnergy(999), '999 Wh');
  assert.equal(formatEnergy(1500), '1.50 kWh');
  assert.equal(formatEnergy(null), '–');
  assert.equal(formatCost(2000, 0.32, 'CHF'), '0.64 CHF');
  assert.equal(formatCost(2000, null), null);
  assert.equal(formatFilament(3.456, null), '3.5 g');
  assert.equal(formatFilament(null, 2345), '2.35 m');
  assert.equal(formatLength(327_360), '327 m');
  assert.equal(formatLength(2345), '2.3 m');
  assert.equal(formatLength(null), '–');
  assert.equal(formatWeight(644.4), '644 g');
  assert.equal(formatWeight(2450), '2.45 kg');
  assert.equal(stripGcodeExtension('Benchy.gcode'), 'Benchy');
  assert.equal(stripGcodeExtension('part.bgcode'), 'part');
  assert.equal(stripGcodeExtension('notes.txt'), 'notes.txt');
});

test('wrapping keeps the lines under the width and ellipsises the last one', () => {
  const ctx = { font: '', measureText: (text) => ({ width: text.length * 10 }) };
  assert.deepEqual(wrapText(ctx, 'one two three four five', 90, 2, { size: 10 }), ['one two', 'three fo…']);
  assert.deepEqual(wrapText(ctx, 'short', 90, 2, { size: 10 }), ['short']);
  assert.deepEqual(wrapText(ctx, 'averyveryverylongword', 90, 1, { size: 10 }), ['averyver…']);
});
