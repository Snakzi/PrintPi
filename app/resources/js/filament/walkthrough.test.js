import assert from 'node:assert/strict';
import { test } from 'node:test';
import { canCancel, endedRecently, isEnded, showsOldFilament, stepActions, stepDescription, stepProgress, stepStatus, stepTitle, stepperSteps } from './walkthrough.js';

const LOAD = ['heating', 'insert', 'loading', 'purging', 'check', 'done'];
const load = (step, extra = {}) => ({ action: 'load', step, steps: LOAD, step_index: LOAD.indexOf(step), nozzle: 215, purges: 0, ...extra });
const CHANGE = ['heating', 'unloading', 'remove', 'heating', 'insert', 'loading', 'purging', 'check', 'done'];

test('every step has a title, the questions read as questions', () => {
  assert.equal(stepTitle(load('heating')), 'Heating to 215 °C');
  assert.equal(stepTitle(load('heating', { target: 260 })), 'Heating to 260 °C', 'a change first heats for the old filament');
  assert.equal(stepTitle(load('insert')), 'Push the filament in until the extruder grips it');
  assert.equal(stepTitle(load('purging')), 'Purging the old colour out');
  assert.equal(stepTitle(load('purging', { purges: 1 })), 'Purging more');
  assert.equal(stepTitle(load('check')), 'Does the filament run clean?');
  assert.equal(stepTitle(load('done')), 'Filament loaded');
  assert.equal(stepTitle({ action: 'unload', step: 'done', steps: [] }), 'Filament unloaded');
  assert.equal(stepTitle(load('error', { error: 'no ok within timeout' })), 'no ok within timeout');
  assert.equal(stepTitle(null), '');
});

test('an ended walkthrough shows its ending where it happened', () => {
  assert.deepEqual(stepperSteps(load('check')), LOAD);
  assert.deepEqual(stepperSteps(load('cancelled', { step_index: 1 })), ['heating', 'cancelled', 'loading', 'purging', 'check', 'done']);
  assert.deepEqual(stepperSteps(load('error', { step_index: 3 })), ['heating', 'insert', 'loading', 'error', 'check', 'done']);
  assert.ok(isEnded(load('done')) && isEnded(load('cancelled')) && isEnded(null));
  assert.ok(!isEnded(load('check')));
});

test('steps before the current one are done, the current one current, the rest upcoming', () => {
  const state = load('loading');
  assert.equal(stepStatus(state, 0), 'done');
  assert.equal(stepStatus(state, 1), 'done');
  assert.equal(stepStatus(state, 2), 'current');
  assert.equal(stepStatus(state, 4), 'upcoming');
  assert.equal(stepStatus(load('done'), 5), 'done');
  assert.equal(stepStatus(load('cancelled', { step_index: 1 }), 1), 'current');
  assert.equal(stepStatus(load('cancelled', { step_index: 1 }), 2), 'upcoming');
  assert.equal(stepStatus(state, 9), 'upcoming');
});

test('a change counts its second heating by position and shows the old filament until it is out', () => {
  const second = { action: 'change', step: 'heating', steps: CHANGE, step_index: 3 };
  assert.equal(stepStatus(second, 0), 'done');
  assert.equal(stepStatus(second, 2), 'done');
  assert.equal(stepStatus(second, 3), 'current');
  assert.equal(stepStatus(second, 4), 'upcoming');
  assert.ok(showsOldFilament({ ...second, step: 'remove', step_index: 2 }));
  assert.ok(!showsOldFilament(second));
  assert.ok(showsOldFilament({ action: 'unload', step: 'done', steps: [] }));
  assert.ok(!showsOldFilament(load('heating')));
});

test('a motion step is timed from the clock, heating carries its own progress', () => {
  const now = 1_000_000;
  const moving = load('loading', { step_started_at: now / 1000 - 3, step_duration: 6 });
  assert.equal(stepProgress(moving, now), 0.5);
  assert.equal(stepProgress({ ...moving, step_started_at: now / 1000 - 60 }, now), 1);
  assert.equal(stepProgress(load('heating', { progress: 0.25 }), now), 0.25);
  assert.equal(stepProgress(load('insert', { progress: null }), now), null);
  assert.equal(stepProgress(load('done', { progress: 1 }), now), null);
});

test('a result is shown for two minutes after the end', () => {
  const now = 2_000_000_000;
  assert.ok(endedRecently(load('done', { finished_at: now / 1000 - 30 }), now));
  assert.ok(!endedRecently(load('done', { finished_at: now / 1000 - 300 }), now));
  assert.ok(!endedRecently(load('check'), now));
});

test('the buttons follow the step', () => {
  assert.deepEqual(stepActions(load('insert')).map((a) => a.id), ['continue']);
  assert.deepEqual(stepActions(load('check')).map((a) => a.id), ['purge', 'yes']);
  assert.deepEqual(stepActions(load('done')).map((a) => a.id), ['close']);
  assert.deepEqual(stepActions(load('heating')), []);
  assert.ok(canCancel(load('heating')));
  assert.ok(!canCancel(load('done')) && !canCancel(null));
});

test('native dialogs direct the user to the printer without suggesting remote answers or progress', () => {
  for (const step of ['printer_unload', 'printer_load']) {
    const state = { backend: 'firmware', step, waiting: false };
    assert.match(stepTitle(state), /printer display/);
    assert.match(stepDescription(state), /printer display/);
    assert.deepEqual(stepActions(state), []);
    assert.equal(canCancel(state), false);
    assert.equal(stepProgress(state), null);
  }
  assert.match(stepDescription({ step: 'printer_load' }), /Insert filament.*colour.*Purge more/);
  assert.match(stepDescription({ step: 'printer_unload' }), /current material.*pull the filament out/);
});

test('native result confirmation explains when to accept or cancel and never offers another host purge', () => {
  for (const step of ['confirm_unloaded', 'confirm_loaded']) {
    const state = { backend: 'firmware', step, waiting: true };
    assert.match(stepDescription(state), /Confirm only.*Cancel/);
    assert.deepEqual(stepActions(state).map((action) => action.id), ['continue']);
    assert.ok(canCancel(state));
  }
});

test('a native change shows the old filament until removal is confirmed', () => {
  const state = { backend: 'firmware', action: 'change', steps: ['printer_unload', 'confirm_unloaded', 'printer_load', 'confirm_loaded', 'done'] };
  assert.ok(showsOldFilament({ ...state, step_index: 0 }));
  assert.ok(showsOldFilament({ ...state, step_index: 1 }));
  assert.ok(!showsOldFilament({ ...state, step_index: 2 }));
  assert.equal(stepStatus({ ...state, step: 'printer_load', step_index: 2 }, 1), 'done');
});
