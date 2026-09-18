export const PHASE_LABELS = {
  queued: 'Waiting',
  downloading: 'Downloading',
  verifying: 'Verifying signature',
  unpacking: 'Unpacking',
  installing: 'Installing',
  switching: 'Switching over',
  done: 'Installed',
  failed: 'Failed',
};

export function phaseLabel(phase) {
  return PHASE_LABELS[phase] ?? '';
}

/** The line under the spinner: the installer's current step, else the phase. */
export function progressLabel(status) {
  return status?.step || phaseLabel(status?.phase);
}

export function formatSize(bytes) {
  if (bytes == null || !Number.isFinite(bytes) || bytes < 0) return '–';
  return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : `${(bytes / 1e6).toFixed(1)} MB`;
}

export function channelLabel(channel) {
  return channel ? channel.charAt(0).toUpperCase() + channel.slice(1) : '';
}
