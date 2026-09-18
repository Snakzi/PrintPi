import assert from 'node:assert/strict';
import { test } from 'node:test';
import { gramsFor, materialMatches, millimetresFor, printIssues, remainingFraction, remainingTone, spoolDetail, uniqueSpoolName } from './spools.js';

const spool = { name: 'Galaxy Black', vendor: 'Prusament', material: 'PLA', diameter: 1.75, density: 1.24, weight: 1000, remaining: 120 };

test('a spool is labelled by vendor, material and finish', () => {
  assert.equal(spoolDetail(spool), 'Prusament · PLA');
  assert.equal(spoolDetail({ material: 'PETG' }), 'PETG');
  assert.equal(spoolDetail({ ...spool, finish: 'glitter' }), 'Prusament · PLA · Glitter');
  assert.equal(spoolDetail({ material: 'PLA', finish: 'velvet' }), 'PLA');
});

test('the remaining fraction drives the bar colour', () => {
  assert.equal(remainingFraction(spool), 0.12);
  assert.equal(remainingFraction({ weight: 0, remaining: 0 }), 0);
  assert.equal(remainingTone(0.5), 'emerald');
  assert.equal(remainingTone(0.2), 'amber');
  assert.equal(remainingTone(0.05), 'red');
});

test('a length is weighed with the spool and a weight measured back', () => {
  assert.ok(Math.abs(gramsFor(spool, 1000) - 2.98) < 0.01);
  assert.equal(gramsFor(spool, null), null);
  assert.ok(Math.abs(millimetresFor(spool, 2.98) - 1000) < 2);
  assert.equal(millimetresFor({ diameter: 0, density: 1.24 }, 5), null);
});

test('materials match loosely', () => {
  assert.ok(materialMatches('PLA', 'pla'));
  assert.ok(materialMatches('PLA', 'PLA+'));
  assert.ok(materialMatches(null, 'PLA'));
  assert.ok(!materialMatches('PETG', 'PLA'));
});

test('the issues name a wrong material and a spool that is too light', () => {
  assert.deepEqual(printIssues({ filament_g: 50, filament_type: 'PLA' }, spool), []);
  assert.deepEqual(printIssues({ filament_g: 150, filament_type: 'PETG' }, spool), ['Sliced for PETG', 'Needs 150 g, 120 g left']);
  assert.deepEqual(printIssues({ filament_mm: 50000 }, spool), ['Needs 149 g, 120 g left']);
  assert.deepEqual(printIssues({ filament_g: 150 }, null), []);
  assert.deepEqual(printIssues(null, spool), []);
});

test('a second spool of the same product gets a number', () => {
  const spools = [{ id: 1, name: 'PLA Galaxy Black' }, { id: 2, name: 'PLA Galaxy Black #2' }, { id: 3, name: 'PLA Galaxy Black Special' }];
  assert.equal(uniqueSpoolName('PLA Galaxy Black', []), 'PLA Galaxy Black');
  assert.equal(uniqueSpoolName('PLA Galaxy Black', spools), 'PLA Galaxy Black #3');
  assert.equal(uniqueSpoolName('PLA Galaxy Black', spools, 2), 'PLA Galaxy Black #2');
  assert.equal(uniqueSpoolName('PLA (Silk)', [{ id: 9, name: 'PLA (Silk)' }]), 'PLA (Silk) #2');
});
