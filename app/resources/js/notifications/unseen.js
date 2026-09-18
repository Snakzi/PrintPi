/**
 * Which of the daemon's notifications are new since the last poll.
 *
 * The daemon keeps the newest notifications in a list; every poll brings the tail of it. The
 * first poll only marks where "now" is, so a reload does not replay what the user already saw,
 * and later polls toast everything that arrived after the newest one seen so far.
 */
export function unseenNotifications(items, seenAt) {
  const newest = items.reduce((max, item) => Math.max(max, Number(item.at) || 0), 0);
  if (seenAt === null || seenAt === undefined) return { fresh: [], seenAt: newest };
  const fresh = items.filter((item) => (Number(item.at) || 0) > seenAt);
  return { fresh, seenAt: Math.max(seenAt, newest) };
}

/** The toast text: "Title: message" when the plugin gave a title. */
export function notificationText(item) {
  return item.title ? `${item.title}: ${item.message}` : item.message;
}

const TOAST_TYPES = { info: 'info', success: 'success', warning: 'warning', error: 'error' };

export function notificationToastType(level) {
  return TOAST_TYPES[level] ?? 'info';
}
