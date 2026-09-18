import { parseGcode, transferables } from './parse.js';

// Receives the raw file bytes, answers with the segment buffers (transferred, not copied).
self.onmessage = ({ data }) => {
  try {
    const result = parseGcode(new TextDecoder().decode(data));
    self.postMessage(result, transferables(result));
  } catch (error) {
    self.postMessage({ error: error.message ?? String(error) });
  }
};
