import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createRenderer, nextTick, ref } from 'vue';
import { useVisible } from './useVisible.js';

function mount(t) {
  const previousDocument = globalThis.document;
  const previousObserver = globalThis.IntersectionObserver;
  const document = new EventTarget();
  document.hidden = false;
  globalThis.document = document;
  let observer;
  globalThis.IntersectionObserver = class {
    constructor(callback) { this.callback = callback; observer = this; }
    observe(target) { this.target = target; }
    disconnect() { this.target = null; }
    intersect(value) { this.callback([{ isIntersecting: value }]); }
  };

  const element = ref({});
  let visible;
  const renderer = createRenderer({ createComment: () => ({}), insert() {}, remove() {} });
  const app = renderer.createApp({
    setup() {
      visible = useVisible(element);
      return () => null;
    },
  });
  app.mount({});
  t.after(() => {
    app.unmount();
    globalThis.document = previousDocument;
    globalThis.IntersectionObserver = previousObserver;
  });
  return { app, element, visible, observer, document };
}

test('widgets are active only inside the viewport and in the foreground tab', (t) => {
  const { visible, observer, document } = mount(t);
  assert.equal(visible.value, false);

  observer.intersect(true);
  assert.equal(visible.value, true);
  document.hidden = true;
  document.dispatchEvent(new Event('visibilitychange'));
  assert.equal(visible.value, false);
  document.hidden = false;
  document.dispatchEvent(new Event('visibilitychange'));
  assert.equal(visible.value, true);
  observer.intersect(false);
  assert.equal(visible.value, false);
});

test('a replaced element waits for its own visibility observation', async (t) => {
  const { element, visible, observer } = mount(t);
  observer.intersect(true);

  element.value = {};
  await nextTick();

  assert.equal(visible.value, false);
  assert.equal(observer.target, element.value);
  observer.intersect(true);
  assert.equal(visible.value, true);
});

test('unmounting disconnects the observer and removes the tab listener', (t) => {
  const { app, visible, observer, document } = mount(t);
  observer.intersect(true);

  app.unmount();
  document.hidden = true;
  document.dispatchEvent(new Event('visibilitychange'));

  assert.equal(observer.target, null);
  assert.equal(visible.value, true);
});
