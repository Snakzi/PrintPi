export const PHASE_LABELS = {
  preparing: 'Preparing',
  flashing: 'Flashing',
  rebooting: 'Restarting the printer',
  reconnecting: 'Reconnecting',
  done: 'Firmware updated',
  failed: 'Failed',
};

export const ACTIVE_PHASES = ['preparing', 'flashing', 'rebooting', 'reconnecting'];

export function phaseLabel(phase) {
  return PHASE_LABELS[phase] ?? '';
}

/** The line under the spinner: the daemon's current step, else the phase. */
export function progressLabel(status) {
  return status?.step || phaseLabel(status?.phase);
}

export const METHOD_LABELS = {
  buddy: 'Flash a .bbf from the USB drive (Prusa Buddy)',
  avrdude: 'avrdude over the serial port (8-bit boards)',
  restart: 'Restart to flash firmware.bin from the SD card',
};

export function methodLabel(method) {
  return METHOD_LABELS[method] ?? method ?? '';
}

/** GitHub release bodies are Markdown; the notes are shown as plain text, so the markup goes. */
export function plainNotes(markdown) {
  if (!markdown) return '';
  return markdown
    .replace(/\r\n/g, '\n')
    .replace(/^#{1,6}[ \t]+/gm, '')
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/(\*\*|__)(.+?)\1/g, '$2')
    .replace(/(^|[^*\w])[*_](\S(?:.*?\S)?)[*_](?=[^*\w]|$)/g, '$1$2')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^[ \t]*[-*+][ \t]+/gm, '• ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}
