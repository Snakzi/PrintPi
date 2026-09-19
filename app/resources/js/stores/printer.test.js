import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createPinia, setActivePinia } from 'pinia';
import { usePrinterStore } from './printer.js';

const state = (connection = 'connected') => ({
  daemon_alive: true,
  printer: { connection, temperatures: { T0: { actual: 200, target: 210 } } },
});

function store() {
  setActivePinia(createPinia());
  return usePrinterStore();
}

test('state and temperatures keep updating without downloading an unused terminal log', async (t) => {
  const printer = store();
  const requests = [];
  t.mock.method(globalThis, 'fetch', async (url) => {
    requests.push(url);
    return Response.json(state());
  });

  await printer.refresh();

  assert.deepEqual(requests, ['/api/v1/printer/state']);
  assert.equal(printer.hotend.actual, 200);
  assert.equal(printer.history.length, 1);
});

test('multiple visible terminals share one log request and hiding the last stops it', async (t) => {
  const printer = store();
  const requests = [];
  const lines = [{ dir: 'rx', line: 'ok', t: 1 }];
  t.mock.method(globalThis, 'fetch', async (url) => {
    requests.push(url);
    return Response.json(url.endsWith('/state') ? state() : { lines });
  });

  printer.serialConsumers = 2;
  await printer.refresh();
  assert.deepEqual(printer.serial, lines);
  printer.serialConsumers = 1;
  await printer.refresh();
  printer.serialConsumers = 0;
  await printer.refresh();

  assert.deepEqual(requests, [
    '/api/v1/printer/state', '/api/v1/printer/serial?limit=300',
    '/api/v1/printer/state', '/api/v1/printer/serial?limit=300',
    '/api/v1/printer/state',
  ]);
});

test('a slow state request cannot accumulate overlapping polls', async (t) => {
  const printer = store();
  let finish;
  const fetch = t.mock.method(globalThis, 'fetch', () => new Promise((resolve) => { finish = resolve; }));

  const first = printer.refresh();
  await printer.refresh();
  await printer.refresh();
  assert.equal(fetch.mock.callCount(), 1);
  finish(Response.json(state()));
  await first;

  assert.equal(printer.refreshing, false);
  assert.equal(printer.history.length, 1);
});

test('the next poll recovers after an API failure', async (t) => {
  const printer = store();
  let fail = true;
  t.mock.method(globalThis, 'fetch', async () => {
    if (fail) throw new Error('Connection lost');
    return Response.json(state());
  });

  await printer.refresh();
  assert.equal(printer.apiError, 'Connection lost');
  fail = false;
  await printer.refresh();

  assert.equal(printer.apiError, null);
  assert.equal(printer.refreshing, false);
  assert.equal(printer.connected, true);
});

test('a disconnected printer clears old data without fetching a visible terminal', async (t) => {
  const printer = store();
  printer.serialConsumers = 1;
  printer.serial = [{ dir: 'rx', line: 'ok', t: 1 }];
  printer.history = [{ t: 1, temps: {} }];
  const fetch = t.mock.method(globalThis, 'fetch', async () => Response.json(state('offline')));

  await printer.refresh();

  assert.equal(fetch.mock.callCount(), 1);
  assert.deepEqual(printer.serial, []);
  assert.deepEqual(printer.history, []);
});
