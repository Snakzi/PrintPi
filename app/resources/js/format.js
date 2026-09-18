export function formatBytes(bytes) {
  if (bytes == null) return '–';
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${unit > 0 && value < 10 ? value.toFixed(1) : Math.round(value)} ${units[unit]}`;
}

export function formatDuration(seconds) {
  if (seconds == null) return '–';
  if (seconds < 60) return `${Math.round(seconds)} s`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  if (hours >= 24) return `${Math.floor(hours / 24)} d ${hours % 24} h`;
  return hours ? `${hours} h ${minutes} min` : `${minutes} min`;
}

/** Seconds as h:mm:ss, or m:ss under an hour; for clocks that tick. */
export function formatHms(seconds) {
  if (seconds == null) return '–';
  const total = Math.max(0, Math.round(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const rest = String(total % 60).padStart(2, '0');
  return hours ? `${hours}:${String(minutes).padStart(2, '0')}:${rest}` : `${minutes}:${rest}`;
}

/** A time of day, prefixed with the weekday when it is not today. */
export function formatClock(ms) {
  const date = new Date(ms);
  const time = date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  if (date.toDateString() === new Date().toDateString()) return time;
  return `${date.toLocaleDateString(undefined, { weekday: 'short' })} ${time}`;
}

export function formatDateTime(iso) {
  return iso ? new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '–';
}

export function formatDate(iso) {
  return iso ? new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' }) : '–';
}

/** Watt hours as Wh below a kilowatt hour, else kWh. */
export function formatEnergy(wh) {
  if (wh == null) return '–';
  return wh >= 1000 ? `${(wh / 1000).toFixed(2)} kWh` : `${Math.round(wh)} Wh`;
}

/** What the energy cost at the configured price per kWh, or null without a price. */
export function formatCost(wh, pricePerKwh, currency = '€') {
  if (wh == null || pricePerKwh == null || pricePerKwh === '') return null;
  return `${((wh / 1000) * Number(pricePerKwh)).toFixed(2)} ${currency}`;
}

/** A mass of filament in grams, or kilograms from one kilogram on. */
export function formatWeight(grams) {
  if (grams == null) return '–';
  return grams >= 1000 ? `${(grams / 1000).toFixed(2)} kg` : `${Math.round(grams)} g`;
}

/** A length of filament in metres, rounded to what a spool label would say. */
export function formatLength(millimetres) {
  if (millimetres == null) return '–';
  const metres = millimetres / 1000;
  return `${metres >= 10 ? Math.round(metres) : metres.toFixed(1)} m`;
}

export function formatFilament(grams, millimetres) {
  if (grams != null) return `${Number(grams).toFixed(grams < 10 ? 1 : 0)} g`;
  if (millimetres != null) return `${(millimetres / 1000).toFixed(2)} m`;
  return '–';
}

export function stripGcodeExtension(name) {
  return name.replace(/\.(gcode|gco|g|nc|bgcode)$/i, '');
}

export function formatTime(ms) {
  return new Date(ms).toLocaleTimeString();
}

export function formatTemp(value, digits = 1) {
  return value == null ? '–' : Number(value).toFixed(digits);
}

export const SENSOR_LABELS = {
  T0: 'Hotend',
  T1: 'Hotend 2',
  T2: 'Hotend 3',
  B: 'Bed',
  C: 'Chamber',
  X: 'Heatbreak',
  A: 'Board',
  P: 'Probe',
  R: 'Redundant',
  L: 'Cooler',
};

export function sensorLabel(key) {
  return SENSOR_LABELS[key] ?? key;
}

export function portLabel(port) {
  if (!port) return '–';
  if (port.device.startsWith('fake://')) return 'Simulated printer';
  const description = port.description && port.description !== 'n/a' ? port.description : null;
  return description ? `${port.device} · ${description}` : port.device;
}

export const BAUD_RATES = [115200, 250000, 230400, 500000, 1000000, 57600, 38400, 19200, 9600];

export function timezones() {
  try {
    return Intl.supportedValuesOf('timeZone');
  } catch {
    return ['Europe/Berlin', 'Europe/Vienna', 'Europe/Zurich', 'Europe/London', 'UTC'];
  }
}

export function browserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Berlin';
  } catch {
    return 'Europe/Berlin';
  }
}

export function cameraLabel(camera) {
  return camera.name ? `${camera.name} (${camera.device})` : camera.device;
}
