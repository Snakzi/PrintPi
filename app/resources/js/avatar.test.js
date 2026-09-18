import assert from 'node:assert/strict';
import { test } from 'node:test';
import { avatarColor, hueOf, initials } from './avatar.js';

test('initials come from the first two words, camel case or the first letters', () => {
  assert.equal(initials('Grace Hopper'), 'GH');
  assert.equal(initials('DevLocal'), 'DL');
  assert.equal(initials('alice'), 'AL');
  assert.equal(initials('max.mustermann'), 'MM');
  assert.equal(initials('ÄBC'), 'ÄB');
  assert.equal(initials('user_42'), 'U4');
  assert.equal(initials(''), '?');
  assert.equal(initials(null), '?');
});

test('the colour is stable and differs between names', () => {
  assert.equal(hueOf('DevLocal'), hueOf('DevLocal'));
  assert.ok(hueOf('DevLocal') >= 0 && hueOf('DevLocal') < 360);
  assert.notEqual(hueOf('alice'), hueOf('bob'));
  assert.match(avatarColor('alice'), /^hsl\(\d+ 50% 42%\)$/);
});
