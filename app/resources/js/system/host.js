/**
 * Readable pieces of the host stats the daemon publishes: uptime and the Pi firmware's
 * throttle flags. `throttleIssues` turns the flags into the lines the settings page lists,
 * worst first; an empty list means the power and the temperature are fine.
 */
const ISSUES = [
  ['under_voltage', 'Under-voltage now', 'danger'],
  ['throttled', 'Throttled now', 'danger'],
  ['temperature_limit', 'Temperature limit active', 'warn'],
  ['frequency_capped', 'Frequency capped', 'warn'],
  ['under_voltage_occurred', 'Under-voltage since boot', 'warn'],
  ['throttled_occurred', 'Throttled since boot', 'warn'],
  ['temperature_limit_occurred', 'Temperature limit since boot', 'muted'],
  ['frequency_capped_occurred', 'Frequency capped since boot', 'muted'],
];

export function throttleIssues(flags) {
  if (!flags) return [];
  return ISSUES.filter(([key]) => flags[key]).map(([, label, tone]) => ({ label, tone }));
}

export function formatUptime(seconds) {
  if (seconds == null) return null;
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days) return `${days} d ${hours} h`;
  if (hours) return `${hours} h ${minutes} min`;
  return `${minutes} min`;
}
