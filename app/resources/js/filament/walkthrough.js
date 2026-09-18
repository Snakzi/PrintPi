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
  printer_unload: 'Unload on printer',
  confirm_unloaded: 'Confirm removal',
  printer_load: 'Load on printer',
  confirm_loaded: 'Confirm loading',
  done: 'Done',
  cancelled: 'Cancelled',
  error: 'Failed',
};

/** The line under the picture: what is happening or what the user has to do now. */
export function stepTitle(state) {
  if (!state) return '';
  switch (state.step) {
    case 'printer_unload':
      return 'Follow the printer display to unload';
    case 'printer_load':
      return 'Follow the printer display to load';
    case 'confirm_unloaded':
      return 'Has the old filament been removed?';
    case 'confirm_loaded':
      return 'Did loading finish successfully?';
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

/** Short instructions shared by the web modal and the touch panel. */
export function stepDescription(state) {
  if (!state) return '';
  switch (state.step) {
    case 'printer_unload':
      return 'Choose the current material on the printer if asked. Wait for unloading, then pull the filament out when prompted. To stop, use the printer display.';
    case 'printer_load':
      return 'Insert filament when the printer asks. Check the colour at the nozzle and choose Yes or Purge more on its display. To stop, use the printer display.';
    case 'confirm_unloaded':
      return 'Confirm only after the printer has finished and you have pulled out the old filament. If you stopped the operation or it failed, choose Cancel.';
    case 'confirm_loaded':
      return 'Confirm only if you accepted the clean colour on the printer. This saves the loaded spool in PrintPi. If you stopped loading or it failed, choose Cancel.';
    case 'heating':
      return 'Wait for the nozzle to reach the required temperature.';
    case 'insert':
      return 'Feed the filament into the extruder, then choose Continue.';
    case 'remove':
      return 'Pull out the loose filament, then choose Continue.';
    case 'loading':
    case 'unloading':
      return 'Wait while the extruder moves the filament.';
    case 'purging':
      return 'Wait for filament to flow from the nozzle.';
    case 'check':
      return 'Choose Yes, clean when only the new colour comes out, or Purge more to flush again.';
    case 'cancelled':
      return state.backend === 'firmware' ? 'The result was not confirmed. Check the filament in the printer before starting again.' : '';
    case 'error':
      return state.backend === 'firmware' ? 'Check the printer display. Finish or stop any open filament dialog there before trying again.' : '';
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
  const remove = (state.steps ?? []).indexOf(state.backend === 'firmware' ? 'confirm_unloaded' : 'remove');
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
    case 'confirm_unloaded':
      return [{ id: 'continue', label: 'Yes, removed', variant: 'primary', icon: 'check' }];
    case 'confirm_loaded':
      return [{ id: 'continue', label: 'Yes, loaded', variant: 'primary', icon: 'check' }];
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

/** Stock Buddy dialogs must be stopped on the printer; only the result check is local. */
export function canCancel(state) {
  return Boolean(state) && !isEnded(state) && (state.backend !== 'firmware' || state.waiting === true);
}
