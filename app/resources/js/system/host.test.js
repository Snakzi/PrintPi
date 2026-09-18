import assert from 'node:assert/strict';
import { test } from 'node:test';
import { formatUptime, throttleIssues } from './host.js';

test('no flags or a clean host give no issues', () => {
  assert.deepEqual(throttleIssues(null), []);
  assert.deepEqual(throttleIssues({ raw: '0x0', under_voltage: false, throttled_occurred: false }), []);
});

test('current problems come first, history after, with their tones', () => {
  const issues = throttleIssues({ under_voltage_occurred: true, temperature_limit: true, temperature_limit_occurred: true });
  assert.deepEqual(issues.map((issue) => issue.label), ['Temperature limit active', 'Under-voltage since boot', 'Temperature limit since boot']);
  assert.deepEqual(issues.map((issue) => issue.tone), ['warn', 'warn', 'muted']);
  assert.equal(throttleIssues({ under_voltage: true })[0].tone, 'danger');
});

test('uptime reads in the largest two units', () => {
  assert.equal(formatUptime(null), null);
  assert.equal(formatUptime(90), '1 min');
  assert.equal(formatUptime(3 * 3600 + 5 * 60), '3 h 5 min');
  assert.equal(formatUptime(2 * 86400 + 3600), '2 d 1 h');
});
