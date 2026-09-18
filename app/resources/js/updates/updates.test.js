import assert from 'node:assert/strict';
import { test } from 'node:test';
import { formatSize, phaseLabel, progressLabel } from './format.js';

test('release sizes use one decimal in MB or GB', () => {
  assert.equal(formatSize(12345678), '12.3 MB');
  assert.equal(formatSize(1250000000), '1.3 GB');
  assert.equal(formatSize(1000000000), '1.0 GB');
  assert.equal(formatSize(0), '0.0 MB');
  assert.equal(formatSize(500000), '0.5 MB');
});

test('missing or invalid release sizes have a placeholder', () => {
  for (const bytes of [null, undefined, NaN, Infinity, -1]) {
    assert.equal(formatSize(bytes), '–');
  }
});

test('update phases have user-facing labels', () => {
  assert.equal(phaseLabel('queued'), 'Waiting');
  assert.equal(phaseLabel('downloading'), 'Downloading');
  assert.equal(phaseLabel('verifying'), 'Verifying signature');
  assert.equal(phaseLabel('unpacking'), 'Unpacking');
  assert.equal(phaseLabel('installing'), 'Installing');
  assert.equal(phaseLabel('switching'), 'Switching over');
  assert.equal(phaseLabel('done'), 'Installed');
  assert.equal(phaseLabel('failed'), 'Failed');
});

test('missing or unknown phases have no label', () => {
  assert.equal(phaseLabel(null), '');
  assert.equal(phaseLabel(undefined), '');
  assert.equal(phaseLabel('unknown'), '');
});

test('the progress line prefers the installer step over the phase', () => {
  assert.equal(progressLabel({ phase: 'installing', step: 'Migrating the database' }), 'Migrating the database');
  assert.equal(progressLabel({ phase: 'switching', step: 'Switching to 0.2.0' }), 'Switching to 0.2.0');
  assert.equal(progressLabel({ phase: 'downloading', step: null }), 'Downloading');
  assert.equal(progressLabel({ phase: 'verifying', step: '' }), 'Verifying signature');
  assert.equal(progressLabel(null), '');
  assert.equal(progressLabel(undefined), '');
});
