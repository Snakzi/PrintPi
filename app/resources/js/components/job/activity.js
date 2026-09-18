/** Labels for what the printer is doing, as the daemon reports it in job.activity: the start G-code before the first layer, a pause or resume script later. */
const LABELS = {
  preparing: 'Preparing',
  heating: 'Heating',
  homing: 'Homing',
  cleaning: 'Cleaning nozzle',
  leveling: 'Leveling',
  purging: 'Purging',
  loading: 'Loading filament',
  pausing: 'Pausing',
  resuming: 'Resuming',
};

export function activityLabel(activity) {
  return LABELS[activity] ?? LABELS.preparing;
}
