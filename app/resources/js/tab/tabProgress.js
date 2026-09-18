import { activityLabel } from '../components/job/activity.js';

/**
 * What the browser tab shows for a print job: the title and the ring around the favicon.
 * The ring is `{fraction, tone}` or null when the plain favicon should show; tones are the
 * palette names the favicon renderer maps to colours. An ended job is only announced with
 * `showEnding`, which the composable sets while the tab was hidden at the end of the print,
 * so the outcome waits in the tab bar until the user looks.
 */
export const BASE_TITLE = 'PrintPi';

const ENDINGS = {
  finished: { label: 'Finished', tone: 'emerald' },
  cancelled: { label: 'Cancelled', tone: 'zinc' },
  error: { label: 'Failed', tone: 'red' },
};

const SCRIPTS = ['pausing', 'resuming'];

export function tabState(job, { showEnding = false } = {}) {
  if (!job) return plain();
  const fraction = Math.min(1, Math.max(0, job.progress ?? 0));
  const percent = Math.round(fraction * 100);

  if (job.state === 'printing' || job.state === 'paused') {
    if (job.activity) {
      const tone = SCRIPTS.includes(job.activity) ? 'amber' : 'sky';
      return titled(activityLabel(job.activity), { fraction: 1, tone });
    }
    if (job.state === 'paused') return titled(`Paused ${percent} %`, { fraction, tone: 'amber' });
    return titled(`${percent} %`, { fraction, tone: 'emerald' });
  }
  if (job.state === 'cancelling') return titled('Cancelling', { fraction, tone: 'amber' });

  const ending = ENDINGS[job.state];
  if (!ending || !showEnding) return plain();
  return titled(ending.label, { fraction: 1, tone: ending.tone });
}

export function isEnded(state) {
  return Boolean(ENDINGS[state]);
}

function plain() {
  return { title: BASE_TITLE, ring: null };
}

function titled(prefix, ring) {
  return { title: `${prefix} · ${BASE_TITLE}`, ring };
}
