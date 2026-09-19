import assert from 'node:assert/strict';
import { test } from 'node:test';
import { renderOnDemand } from './renderOnDemand.js';

function frames() {
  let id = 0;
  const pending = new Map();
  return {
    requestFrame(callback) { pending.set(++id, callback); return id; },
    cancelFrame(frame) { pending.delete(frame); },
    tick() {
      const callbacks = [...pending.values()];
      pending.clear();
      callbacks.forEach((callback) => callback());
    },
    get pending() { return pending.size; },
  };
}

test('an unchanged visible scene renders once and then stays idle', () => {
  const clock = frames();
  let draws = 0;
  const rendering = renderOnDemand(() => { draws += 1; }, clock);

  rendering.setVisible(true);
  clock.tick();
  for (let i = 0; i < 120; i += 1) clock.tick();

  assert.equal(draws, 1);
  assert.equal(clock.pending, 0);
});

test('multiple progress and resize updates draw only the latest state in one frame', () => {
  const clock = frames();
  let line = 0;
  const drawn = [];
  const rendering = renderOnDemand(() => { drawn.push(line); }, clock);
  rendering.setVisible(true);
  clock.tick();

  for (let next = 1; next <= 10; next += 1) {
    line = next;
    rendering.request();
  }
  clock.tick();

  assert.deepEqual(drawn, [0, 10]);
  assert.equal(clock.pending, 0);
});

test('camera damping continues until movement settles without duplicate frames', () => {
  const clock = frames();
  let draws = 0;
  const rendering = renderOnDemand(() => {
    draws += 1;
    if (draws < 4) {
      rendering.request(); // OrbitControls also dispatches change during update().
      return true;
    }
    return false;
  }, clock);

  rendering.setVisible(true);
  for (let i = 0; i < 8; i += 1) clock.tick();

  assert.equal(draws, 4);
  assert.equal(clock.pending, 0);
});

test('offscreen updates do no work and the latest state appears when visible again', () => {
  const clock = frames();
  let line = 0;
  const drawn = [];
  const rendering = renderOnDemand(() => { drawn.push(line); }, clock);
  rendering.setVisible(true);
  rendering.setVisible(false);

  line = 200;
  rendering.request();
  clock.tick();
  assert.deepEqual(drawn, []);

  line = 400;
  rendering.setVisible(true);
  clock.tick();
  assert.deepEqual(drawn, [400]);
});

test('disposing a viewer cancels pending work and prevents later renders', () => {
  const clock = frames();
  let draws = 0;
  const rendering = renderOnDemand(() => { draws += 1; return true; }, clock);
  rendering.setVisible(true);

  rendering.dispose();
  rendering.request();
  rendering.setVisible(false);
  rendering.setVisible(true);
  clock.tick();

  assert.equal(draws, 0);
  assert.equal(clock.pending, 0);
});
