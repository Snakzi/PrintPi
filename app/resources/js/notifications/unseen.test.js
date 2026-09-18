import assert from 'node:assert/strict';
import { test } from 'node:test';
import { notificationText, notificationToastType, unseenNotifications } from './unseen.js';

const note = (at, message = 'm') => ({ id: String(at), at, level: 'info', message });

test('the first poll marks the newest notification as seen without toasting', () => {
  assert.deepEqual(unseenNotifications([note(10), note(20)], null), { fresh: [], seenAt: 20 });
  assert.deepEqual(unseenNotifications([], null), { fresh: [], seenAt: 0 });
});

test('later polls report what arrived after the last seen one', () => {
  const { fresh, seenAt } = unseenNotifications([note(10), note(20), note(30)], 20);
  assert.deepEqual(fresh.map((item) => item.at), [30]);
  assert.equal(seenAt, 30);
  assert.deepEqual(unseenNotifications([note(10)], 30), { fresh: [], seenAt: 30 });
});

test('texts carry the title and levels map to toast types', () => {
  assert.equal(notificationText({ title: 'Plug', message: 'off' }), 'Plug: off');
  assert.equal(notificationText({ title: null, message: 'off' }), 'off');
  assert.equal(notificationToastType('warning'), 'warning');
  assert.equal(notificationToastType('loud'), 'info');
});
