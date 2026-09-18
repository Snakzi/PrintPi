import assert from 'node:assert/strict';
import { test } from 'node:test';
import { hexToHsv, hsvToHex, hsvToRgb, normalizeHex, parseHex, rgbToHsv } from './hsv.js';

test('a hex colour parses in either case with or without the hash', () => {
  assert.deepEqual(parseHex('#FF8000'), { r: 255, g: 128, b: 0 });
  assert.deepEqual(parseHex('ff8000'), { r: 255, g: 128, b: 0 });
  assert.equal(parseHex('#fff'), null);
  assert.equal(parseHex('red'), null);
  assert.equal(parseHex(null), null);
  assert.equal(normalizeHex(' FF8000 '), '#ff8000');
  assert.equal(normalizeHex('#12345g'), null);
});

test('the primaries land on their hue with full saturation', () => {
  assert.deepEqual(hexToHsv('#ff0000'), { h: 0, s: 1, v: 1 });
  assert.deepEqual(hexToHsv('#00ff00'), { h: 120, s: 1, v: 1 });
  assert.deepEqual(hexToHsv('#0000ff'), { h: 240, s: 1, v: 1 });
  assert.deepEqual(hexToHsv('#ffffff'), { h: 0, s: 0, v: 1 });
  assert.deepEqual(hexToHsv('#000000'), { h: 0, s: 0, v: 0 });
  assert.deepEqual(rgbToHsv({ r: 128, g: 128, b: 128 }), { h: 0, s: 0, v: 128 / 255 });
});

test('hsv converts back to the same hex', () => {
  for (const hex of ['#ff8000', '#123456', '#abcdef', '#7f7f7f', '#00ffff', '#ff00ff', '#010203']) {
    assert.equal(hsvToHex(hexToHsv(hex)), hex, hex);
  }
  assert.equal(hsvToHex({ h: 360, s: 1, v: 1 }), '#ff0000');
  assert.equal(hsvToHex({ h: -120, s: 1, v: 1 }), '#0000ff');
  assert.deepEqual(hsvToRgb({ h: 30, s: 1, v: 1 }), { r: 255, g: 128, b: 0 });
});

test('the hue keeps the tint when only saturation or value change', () => {
  const hsv = { h: 30, s: 1, v: 1 };
  assert.equal(hsvToHex({ ...hsv, s: 0.5 }), '#ffbf80');
  assert.equal(hsvToHex({ ...hsv, v: 0.5 }), '#804000');
  assert.equal(hsvToHex({ ...hsv, s: 0 }), '#ffffff');
});
