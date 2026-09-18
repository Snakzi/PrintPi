import { defineStore } from 'pinia';
import { markRaw } from 'vue';
import { downloadBytes } from '../api';

/** Parsed models kept in memory; the file preview, the live preview and the job widget share one parse of a file. */
const KEEP = 2;

export function modelKey(file) {
  return `${file.id}:${file.uploaded_at ?? ''}`;
}

/**
 * The parse worker. Under the Vite dev server the script lives on another origin than the
 * page (port 5173 against 8000) and a Worker refuses a cross-origin URL, so there it is
 * started from a same-origin blob that imports the script; the production bundle serves
 * it from the page's own origin and takes the direct route.
 */
function createWorker() {
  if (import.meta.env.DEV) {
    // Resolved by hand so Vite does not also emit the raw script as an asset of the build.
    const base = import.meta.url;
    const url = new URL('../gcode/parse.worker.js', base);
    if (url.origin !== window.location.origin) {
      const blob = new Blob([`import ${JSON.stringify(url.href)};`], { type: 'text/javascript' });
      return new Worker(URL.createObjectURL(blob), { type: 'module' });
    }
  }
  return new Worker(new URL('../gcode/parse.worker.js', import.meta.url), { type: 'module' });
}

function parseInWorker(bytes) {
  return new Promise((resolve, reject) => {
    const worker = createWorker();
    worker.onmessage = ({ data }) => {
      worker.terminate();
      if (data.error) reject(new Error(data.error));
      else resolve(data);
    };
    worker.onerror = (event) => {
      worker.terminate();
      reject(new Error(event.message || 'Could not parse the file'));
    };
    worker.postMessage(bytes.buffer, [bytes.buffer]);
  });
}

export const useGcodeModelStore = defineStore('gcodeModels', {
  // key → { phase: loading | parsing | ready | error, progress, error, model }
  state: () => ({ entries: {} }),

  getters: {
    entryFor: (state) => (file) => (file ? (state.entries[modelKey(file)] ?? null) : null),
  },

  actions: {
    /** Starts downloading and parsing unless the file is already known; returns the reactive entry. */
    load(file) {
      const key = modelKey(file);
      if (this.entries[key]) return this.entries[key];
      for (const stale of Object.keys(this.entries).slice(0, Math.max(0, Object.keys(this.entries).length - (KEEP - 1)))) {
        delete this.entries[stale];
      }
      this.entries[key] = { key, phase: 'loading', progress: 0, error: null, model: null };
      this.fetch(file, key);
      return this.entries[key];
    },

    async fetch(file, key) {
      const entry = () => this.entries[key];
      try {
        const bytes = await downloadBytes(file.download_url, {
          size: file.size,
          onProgress: (value) => {
            if (entry()) entry().progress = value;
          },
        });
        if (!entry()) return;
        entry().phase = 'parsing';
        const parsed = await parseInWorker(bytes);
        if (!entry()) return;
        entry().model = markRaw(parsed);
        entry().phase = 'ready';
      } catch (error) {
        if (!entry()) return;
        entry().error = error.message;
        entry().phase = 'error';
      }
    },

    forget(file) {
      delete this.entries[modelKey(file)];
    },
  },
});
