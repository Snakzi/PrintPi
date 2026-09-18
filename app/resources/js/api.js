export class ApiError extends Error {
  constructor(message, status, errors = null) {
    super(message);
    this.status = status;
    this.errors = errors;
  }
}

function messageFrom(data, fallback) {
  const firstError = data?.errors ? Object.values(data.errors).flat()[0] : null;
  return firstError || data?.message || fallback;
}

/** Laravel sets the XSRF-TOKEN cookie; sending it back as a header satisfies the CSRF check. */
function xsrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)XSRF-TOKEN=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function unauthenticated() {
  window.dispatchEvent(new CustomEvent('printpi:unauthenticated'));
}

export async function api(path, { method = 'GET', body, headers = {} } = {}) {
  const init = { method, headers: { Accept: 'application/json', ...headers }, credentials: 'same-origin' };
  if (method !== 'GET') {
    const token = xsrfToken();
    if (token) init.headers['X-XSRF-TOKEN'] = token;
  }
  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  const response = await fetch(`/api/v1/${path}`, init);
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401) unauthenticated();
    throw new ApiError(messageFrom(data, `${response.status} ${response.statusText}`), response.status, data?.errors ?? null);
  }
  return data;
}

/** Multipart upload with progress, which fetch() cannot report. */
export function upload(path, file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/api/v1/${path}`);
    xhr.setRequestHeader('Accept', 'application/json');
    const token = xsrfToken();
    if (token) xhr.setRequestHeader('X-XSRF-TOKEN', token);
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) onProgress(event.loaded / event.total);
    });
    xhr.addEventListener('load', () => {
      let data = null;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        // not JSON, keep null
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data);
      } else {
        if (xhr.status === 401) unauthenticated();
        reject(new ApiError(messageFrom(data, `${xhr.status} ${xhr.statusText}`), xhr.status, data?.errors ?? null));
      }
    });
    xhr.addEventListener('error', () => reject(new ApiError('Netzwerkfehler beim Upload', 0)));
    const form = new FormData();
    form.append('file', file);
    xhr.send(form);
  });
}

/**
 * Streams a file the API serves (a download_url) into memory, reporting progress
 * against Content-Length or the given size hint.
 */
export async function downloadBytes(url, { onProgress, signal, size = 0 } = {}) {
  const response = await fetch(url, { credentials: 'same-origin', signal });
  if (!response.ok) {
    if (response.status === 401) unauthenticated();
    throw new ApiError(`${response.status} ${response.statusText}`, response.status);
  }
  const total = Number(response.headers.get('Content-Length')) || size;
  const reader = response.body.getReader();
  const chunks = [];
  let received = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    received += value.length;
    if (onProgress && total) onProgress(Math.min(received / total, 1));
  }
  const bytes = new Uint8Array(received);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.length;
  }
  return bytes;
}
