import assert from 'node:assert/strict';
import { test } from 'node:test';
import { DAY, HOUR, MINUTE, MIN_SPAN, clampWindow, nearestIndex, panWindow, resolveWindow, tickStep, timeTicks, visibleRuns, zoomWindow } from './timeWindow.js';

const now = Date.UTC(2026, 8, 16, 12, 0);
const utc = () => 0;

test('a live window ends at the clock and a fixed one where it was left', () => {
  assert.deepEqual(resolveWindow({ span: HOUR, to: null }, now), { from: now - HOUR, to: now });
  assert.deepEqual(resolveWindow({ span: HOUR, to: now - DAY / 2 }, now), { from: now - DAY / 2 - HOUR, to: now - DAY / 2 });
});

test('clamping keeps the window inside the day and snaps a recent end to live', () => {
  assert.deepEqual(clampWindow({ span: 2 * DAY, to: null }, now), { span: DAY, to: null });
  assert.deepEqual(clampWindow({ span: 10, to: null }, now), { span: MIN_SPAN, to: null });
  assert.deepEqual(clampWindow({ span: HOUR, to: now - 30_000 }, now), { span: HOUR, to: null });
  assert.deepEqual(clampWindow({ span: HOUR, to: now - 2 * DAY }, now), { span: HOUR, to: now - DAY + HOUR });
});

test('zooming keeps the time under the pointer in place', () => {
  const zoomed = zoomWindow({ span: 4 * HOUR, to: null }, 0.5, 0.25, now);
  assert.equal(zoomed.span, 2 * HOUR);
  const { from } = resolveWindow(zoomed, now);
  assert.equal(from + 0.25 * zoomed.span, now - 4 * HOUR + 0.25 * 4 * HOUR); // the pivot stays at a quarter
  assert.deepEqual(zoomWindow({ span: HOUR, to: null }, 0.5, 1, now), { span: 30 * MINUTE, to: null }); // at the right edge it stays live
  assert.deepEqual(zoomWindow({ span: HOUR, to: null }, 100, 0.5, now), { span: DAY, to: null });
});

test('panning moves by a fraction of the span and stops at both ends', () => {
  assert.deepEqual(panWindow({ span: HOUR, to: now - 6 * HOUR }, -1, now), { span: HOUR, to: now - 7 * HOUR });
  assert.deepEqual(panWindow({ span: HOUR, to: now - 6 * HOUR }, 10, now), { span: HOUR, to: null });
  assert.deepEqual(panWindow({ span: HOUR, to: null }, -100, now), { span: HOUR, to: now - DAY + HOUR });
});

test('ticks sit on round local times at a step that fits the width', () => {
  assert.equal(tickStep(DAY, 8), 3 * HOUR);
  assert.equal(tickStep(HOUR, 8), 10 * MINUTE);
  assert.equal(tickStep(5 * MINUTE, 6), MINUTE);
  const ticks = timeTicks(now - 2 * HOUR + 7 * MINUTE, now, 4, utc);
  assert.deepEqual(
    ticks.map((tick) => tick.t),
    [now - 90 * MINUTE, now - 60 * MINUTE, now - 30 * MINUTE, now],
  );
  assert.ok(ticks.every((tick) => tick.step === 30 * MINUTE));
  const day = timeTicks(now - DAY, now, 8, utc);
  assert.deepEqual(day.filter((tick) => tick.midnight).map((tick) => tick.t), [Date.UTC(2026, 8, 16)]);
  const shifted = timeTicks(now - 2 * HOUR, now, 2, () => 30 * MINUTE); // a zone half an hour behind UTC has its full hours at xx:30
  assert.deepEqual(shifted.map((tick) => tick.t), [now - 90 * MINUTE, now - 30 * MINUTE]);
});

test('runs break at missing values and at gaps, and reach one point past the edges', () => {
  const points = [0, 30, 60, 90, 300, 330, 360].map((seconds, index) => ({
    t: seconds * 1000,
    cpu: index === 2 ? null : index * 10,
  }));
  const runs = visibleRuns(points, 'cpu', 45_000, 320_000, 30_000);
  assert.deepEqual(runs, [
    [[30_000, 10]],
    [[90_000, 30]],
    [[300_000, 40], [330_000, 50]],
  ]);
});

test('the nearest point is found by time', () => {
  const points = [10, 20, 30].map((t) => ({ t }));
  assert.equal(nearestIndex(points, 0), 0);
  assert.equal(nearestIndex(points, 24), 1);
  assert.equal(nearestIndex(points, 26), 2);
  assert.equal(nearestIndex(points, 99), 2);
  assert.equal(nearestIndex([], 5), -1);
});
