import assert from 'node:assert/strict';
import { test } from 'node:test';
import { isEnded, tabState } from './tabProgress.js';

test('no job leaves the plain title without a ring', () => {
  assert.deepEqual(tabState(null), { title: 'PrintPi', ring: null });
});

test('a running print shows the rounded percent with an emerald ring', () => {
  const state = tabState({ state: 'printing', progress: 0.4249, activity: null });
  assert.equal(state.title, '42 % · PrintPi');
  assert.deepEqual(state.ring, { fraction: 0.4249, tone: 'emerald' });
});

test('the start G-code shows the activity with a full sky ring', () => {
  const state = tabState({ state: 'printing', progress: 0, activity: 'heating' });
  assert.equal(state.title, 'Heating · PrintPi');
  assert.deepEqual(state.ring, { fraction: 1, tone: 'sky' });
});

test('pause and resume scripts are amber', () => {
  assert.deepEqual(tabState({ state: 'printing', progress: 0.5, activity: 'pausing' }).ring, { fraction: 1, tone: 'amber' });
  assert.equal(tabState({ state: 'paused', progress: 0.5, activity: 'resuming' }).title, 'Resuming · PrintPi');
});

test('a paused print keeps its percent in amber', () => {
  const state = tabState({ state: 'paused', progress: 0.5, activity: null });
  assert.equal(state.title, 'Paused 50 % · PrintPi');
  assert.equal(state.ring.tone, 'amber');
});

test('cancelling holds the progress in amber', () => {
  const state = tabState({ state: 'cancelling', progress: 0.7 });
  assert.equal(state.title, 'Cancelling · PrintPi');
  assert.deepEqual(state.ring, { fraction: 0.7, tone: 'amber' });
});

test('an ended job is plain unless the ending is to be shown', () => {
  const job = { state: 'finished', progress: 1 };
  assert.deepEqual(tabState(job), { title: 'PrintPi', ring: null });
  assert.deepEqual(tabState(job, { showEnding: true }), { title: 'Finished · PrintPi', ring: { fraction: 1, tone: 'emerald' } });
  assert.equal(tabState({ state: 'error', progress: 0.3 }, { showEnding: true }).ring.tone, 'red');
  assert.equal(tabState({ state: 'cancelled', progress: 0.3 }, { showEnding: true }).title, 'Cancelled · PrintPi');
});

test('progress outside 0..1 is clamped', () => {
  assert.equal(tabState({ state: 'printing', progress: 1.2 }).title, '100 % · PrintPi');
  assert.equal(tabState({ state: 'printing', progress: null }).title, '0 % · PrintPi');
});

test('isEnded knows the final states', () => {
  assert.ok(isEnded('finished') && isEnded('cancelled') && isEnded('error'));
  assert.ok(!isEnded('printing') && !isEnded('paused') && !isEnded(undefined));
});
