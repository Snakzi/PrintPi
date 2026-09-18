/**
 * Pure helpers around the daemon's filament walkthrough (daemon/printpi_daemon/filament.py):
 * what each step is called, what the user is asked to do, how far the current step is
 * and which buttons it needs. Shared by the touch panel and the web app's modal.
 */

export const ACTION_LABELS = { load: 'Load filament', unload: 'Unload filament', change: 'Change filament' };

/** The words on the stepper. */
export const STEP_LABELS = {
  heating: 'Heating',
  unloading: 'Unloading',
  remove: 'Remove',
  insert: 'Insert',
  loading: 'Loading',
  purging: 'Purging',
  check: 'Colour',
  done: 'Done',
  cancelled: 'Cancelled',
  error: 'Failed',
};

/** The line under the picture: what is happening or what the user has to do now. */
export function stepTitle(state) {
  if (!state) return '';
  switch (state.step) {
    case 'heating':
      return state.target || state.nozzle ? `Heating to ${state.target || state.nozzle} °C` : 'Heating';
    case 'unloading':
      return 'Pulling the filament out';
    case 'remove':
      return 'Pull the filament out of the extruder';
    case 'insert':
      return 'Push the filament in until the extruder grips it';
    case 'loading':
      return 'Feeding the filament to the nozzle';
    case 'purging':
      return state.purges > 0 ? 'Purging more' : 'Purging the old colour out';
    case 'check':
      return 'Does the filament run clean?';
    case 'done':
      return state.action === 'unload' ? 'Filament unloaded' : 'Filament loaded';
    case 'cancelled':
      return 'Cancelled';
    case 'error':
      return state.error || 'Failed';
    default:
      return '';
  }
}

/** Whether the walkthrough is over, one way or the other. */
export function isEnded(state) {
  return !state || ['done', 'cancelled', 'error'].includes(state.step);
}

/** How long an ended walkthrough keeps showing its result to a screen that has not closed it. */
export const RESULT_SHOWN_FOR_MS = 120_000;

/** Whether an ended walkthrough is still worth showing: it ended within the last two minutes. */
export function endedRecently(state, now = Date.now()) {
  return Boolean(state?.finished_at) && now - state.finished_at * 1000 < RESULT_SHOWN_FOR_MS;
}

/** The steps the stepper shows: the action's own, with a cancel or an error in place of the step it happened on. */
export function stepperSteps(state) {
  if (!state) return [];
  const steps = state.steps ?? [];
  if (state.step === 'cancelled' || state.step === 'error') return steps.map((step, index) => (index === state.step_index ? state.step : step));
  return steps;
}

/**
 * done | current | upcoming for the step at a position of the stepper. Positions, not names: a
 * change heats twice, and the daemon says which heating it is on through `step_index`.
 */
export function stepStatus(state, index) {
  const steps = stepperSteps(state);
  const current = typeof state?.step_index === 'number' ? state.step_index : steps.indexOf(state?.step);
  if (index < 0 || index >= steps.length || current === -1) return 'upcoming';
  if (index < current) return 'done';
  if (index === current) return isEnded(state) && state.step === 'done' ? 'done' : 'current';
  return 'upcoming';
}

/** Whether a change is still on the filament coming out: everything up to and including the remove step. */
export function showsOldFilament(state) {
  if (!state) return false;
  if (state.action === 'unload') return true;
  if (state.action !== 'change') return false;
  const remove = (state.steps ?? []).indexOf('remove');
  return remove !== -1 && (state.step_index ?? 0) <= remove;
}

/**
 * How far the current step is, 0..1, or null when it has no measure. A motion step is timed
 * from `step_started_at` and `step_duration` so the bar moves between polls; heating carries the
 * daemon's own figure.
 */
export function stepProgress(state, now = Date.now()) {
  if (!state || isEnded(state)) return null;
  if (state.step_duration) {
    const elapsed = now / 1000 - state.step_started_at;
    return Math.min(1, Math.max(0, elapsed / state.step_duration));
  }
  return typeof state.progress === 'number' ? Math.min(1, Math.max(0, state.progress)) : null;
}

/**
 * The buttons of the current step: [{ id, label, variant, icon }]. `continue` and the
 * answers go to the daemon, `close` only dismisses an ended walkthrough.
 */
export function stepActions(state) {
  if (!state) return [];
  switch (state.step) {
    case 'insert':
    case 'remove':
      return [{ id: 'continue', label: 'Continue', variant: 'primary', icon: 'check' }];
    case 'check':
      return [
        { id: 'purge', label: 'Purge more', variant: 'secondary', icon: 'arrow-down' },
        { id: 'yes', label: 'Yes, clean', variant: 'primary', icon: 'check' },
      ];
    case 'done':
    case 'cancelled':
    case 'error':
      return [{ id: 'close', label: 'Done', variant: 'primary', icon: 'check' }];
    default:
      return [];
  }
}

/** Whether the step can still be cancelled: anything before the end. */
export function canCancel(state) {
  return Boolean(state) && !isEnded(state);
}
