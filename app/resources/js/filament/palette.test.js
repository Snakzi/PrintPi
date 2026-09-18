import assert from 'node:assert/strict';
import { test } from 'node:test';
import { colorOrder, hexToHsl, isNeutral, paletteColumns, paletteLayout, paletteSummary, paletteTiles } from './palette.js';

const spool = (overrides) => ({ name: 'Spool', vendor: 'Prusament', material: 'PLA', color: '#ff0000', remaining: 500, ...overrides });

test('hex colours convert to hue, saturation and lightness', () => {
  assert.deepEqual(hexToHsl('#ff0000'), { h: 0, s: 1, l: 0.5, c: 1 });
  assert.equal(Math.round(hexToHsl('#00ff00').h), 120);
  assert.equal(Math.round(hexToHsl('#0000ff').h), 240);
  assert.deepEqual(hexToHsl('#808080').s, 0);
  assert.equal(hexToHsl(null), null);
  assert.equal(hexToHsl('red'), null);
});

test('white, grey and black read as neutral, a pale blue does not', () => {
  assert.ok(isNeutral(hexToHsl('#ffffff')));
  assert.ok(isNeutral(hexToHsl('#1a1a1a')));
  assert.ok(isNeutral(hexToHsl('#7a7d80')));
  assert.ok(isNeutral(hexToHsl('#f4efe6')));
  assert.ok(!isNeutral(hexToHsl('#7ab8e0')));
  assert.ok(!isNeutral(hexToHsl('#0a1a3a')));
});

test('colours sort like a rainbow, then greys from white to black, then no colour', () => {
  const ordered = ['#e0115f', '#ff0000', '#ff8800', '#ffee00', '#22cc44', '#2266ff', '#8833cc', '#ffffff', '#f4efe6', '#808080', '#111111', null];
  const shuffled = [...ordered].reverse();
  assert.deepEqual(
    shuffled.sort((a, b) => colorOrder(a) - colorOrder(b)),
    ordered,
  );
});

test('spools of one colour, finish, material and vendor become one tile with the sum of what is left', () => {
  const tiles = paletteTiles([
    spool({ name: 'Galaxy Black', color: '#1a1a1a', finish: 'glitter', remaining: 300 }),
    spool({ name: 'Lipstick Red', color: '#e0115f', remaining: 800 }),
    spool({ name: 'Galaxy Black', color: '#1A1A1A', finish: 'glitter', remaining: 700 }),
    spool({ name: 'Galaxy Black', color: '#1a1a1a', material: 'PETG', finish: 'glitter', remaining: 100 }),
    spool({ name: 'Jet Black', color: '#1a1a1a', remaining: 50 }),
  ]);
  assert.deepEqual(
    tiles.map((tile) => [tile.name, tile.material, tile.finish, tile.count, tile.remaining]),
    [
      ['Lipstick Red', 'PLA', null, 1, 800],
      ['Galaxy Black', 'PLA', 'glitter', 2, 1000],
      ['Galaxy Black', 'PETG', 'glitter', 1, 100],
      ['Jet Black', 'PLA', null, 1, 50],
    ],
  );
  assert.equal(tiles[1].color, '#1a1a1a');
});

test('the grid grows with the inventory and the card with the rows', () => {
  assert.equal(paletteColumns(1), 2);
  assert.equal(paletteColumns(6), 3);
  assert.equal(paletteColumns(12), 5);
  assert.equal(paletteColumns(40), 6);
  const layout = paletteLayout(7, 1096);
  assert.equal(layout.columns, 4);
  assert.equal(layout.rows, 2);
  assert.equal(layout.tileWidth, (1096 - 3 * 20) / 4);
  assert.equal(layout.height, 2 * layout.tileHeight + 20);
  assert.equal(paletteLayout(0, 1096).rows, 1);
});

test('the summary counts spools, names the materials and sums what is left', () => {
  assert.equal(paletteSummary([spool({ remaining: 750 })]), '1 spool · PLA · 750 g left');
  assert.equal(
    paletteSummary([spool({ remaining: 750 }), spool({ material: 'PETG', remaining: 500 }), spool({ material: null, remaining: 0 })]),
    '3 spools · PLA, PETG · 1.25 kg left',
  );
  const many = ['PLA', 'PETG', 'ASA', 'TPU', 'PC'].map((material) => spool({ material }));
  assert.equal(paletteSummary(many), '5 spools · 5 materials · 2.50 kg left');
});
