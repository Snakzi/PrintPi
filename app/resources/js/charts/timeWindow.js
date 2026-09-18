/* The time window of a zoomable chart and the ticks along it. A window is { span, to } in ms; `to`
   null means the window ends now and slides along with the clock. Pure, so node can test it. */

export const MINUTE = 60_000;
export const HOUR = 60 * MINUTE;
export const DAY = 24 * HOUR;
export const MIN_SPAN = 5 * MINUTE;

/** Snapping distance to "now": a window ending this close to the clock follows it. */
const LIVE_TOLERANCE = MINUTE;

const STEPS = [MINUTE, 2 * MINUTE, 5 * MINUTE, 10 * MINUTE, 15 * MINUTE, 30 * MINUTE, HOUR, 2 * HOUR, 3 * HOUR, 6 * HOUR, 12 * HOUR, DAY];

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

/** The window as absolute times. */
export function resolveWindow({ span, to }, now) {
  const end = to ?? now;
  return { from: end - span, to: end };
}

/** Keeps the window inside the last `maxSpan` and snaps an end near the clock to it. */
export function clampWindow({ span, to }, now, maxSpan = DAY) {
  const clampedSpan = clamp(span, MIN_SPAN, maxSpan);
  if (to == null || to >= now - LIVE_TOLERANCE) return { span: clampedSpan, to: null };
  return { span: clampedSpan, to: clamp(to, now - maxSpan + clampedSpan, now) };
}

/** Scales the span by `factor` around the time at `anchor` (0 at the left edge, 1 at the right). */
export function zoomWindow(window, factor, anchor, now, maxSpan = DAY) {
  const { from, to } = resolveWindow(window, now);
  const span = clamp((to - from) * factor, MIN_SPAN, maxSpan);
  const pivot = from + clamp(anchor, 0, 1) * (to - from);
  return clampWindow({ span, to: pivot + (1 - clamp(anchor, 0, 1)) * span }, now, maxSpan);
}

/** Shifts the window by a fraction of its span, positive towards the present. */
export function panWindow(window, fraction, now, maxSpan = DAY) {
  const { to } = resolveWindow(window, now);
  return clampWindow({ span: window.span, to: to + fraction * window.span }, now, maxSpan);
}

/** The coarsest-necessary step so that at most `maxCount` ticks fit into the span. */
export function tickStep(span, maxCount) {
  return STEPS.find((step) => span / step <= Math.max(1, maxCount)) ?? STEPS[STEPS.length - 1];
}

/**
 * Tick times aligned to round local clock times (every full hour, every 15 minutes …).
 * `offset` gives the zone offset in ms at a time, the browser's by default.
 */
export function timeTicks(from, to, maxCount, offset = (t) => new Date(t).getTimezoneOffset() * MINUTE) {
  const step = tickStep(to - from, maxCount);
  const ticks = [];
  for (let t = Math.ceil((from - offset(from)) / step) * step + offset(from); t <= to; t += step) {
    ticks.push({ t, step, midnight: (t - offset(t)) % DAY === 0 });
  }
  return ticks;
}

/**
 * Continuous runs of `[t, value]` of one series within the window, plus one point beyond each edge
 * so the line reaches the border. A missing value or a gap longer than the daemon's interval
 * allows (a restart, a reboot) breaks the line instead of bridging it.
 */
export function visibleRuns(points, key, from, to, interval) {
  const runs = [];
  let run = null;
  let previous = null;
  for (const point of points) {
    if (point.t < from - interval || point.t > to + interval) continue;
    const value = point[key];
    if (value == null || (previous && point.t - previous.t > interval * 2.5)) run = null;
    if (value != null) {
      if (!run) runs.push((run = []));
      run.push([point.t, value]);
    }
    previous = point;
  }
  return runs;
}

/** The index of the point closest to `t`, or -1 without points; the list is sorted by time. */
export function nearestIndex(points, t) {
  if (!points.length) return -1;
  let low = 0;
  let high = points.length - 1;
  while (low < high) {
    const middle = (low + high) >> 1;
    if (points[middle].t < t) low = middle + 1;
    else high = middle;
  }
  if (low > 0 && t - points[low - 1].t < points[low].t - t) return low - 1;
  return low;
}
