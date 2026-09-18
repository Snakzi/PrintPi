import { computed, onMounted, ref, watch } from 'vue';
import { useFileStore } from '../stores/files';
import { useFilamentStore } from '../stores/filament';
import { usePrinterStore } from '../stores/printer';
import { usePrintStartStore } from '../stores/printStart';
import { useToastStore } from '../stores/toasts';
import { gramsNeeded, printIssues } from '../filament/spools';
import { formatDuration, formatFilament } from '../format';

/**
 * The spool question before a print, shared by the modal of the web app and the touch
 * panel's screen: the file from the printStart store, the chosen spool (the loaded one to
 * begin with), why the file would not fit it, and `start`, which loads or unloads the
 * chosen spool first so the history books the print on it.
 */
export function useSpoolChoice() {
  const printStart = usePrintStartStore();
  const filament = useFilamentStore();
  const files = useFileStore();
  const printer = usePrinterStore();
  const toasts = useToastStore();

  const file = computed(() => printStart.file);
  const metadata = computed(() => file.value?.metadata ?? null);
  const selected = ref(null);
  const busy = ref(false);

  onMounted(async () => {
    try {
      await filament.ensure();
    } catch (error) {
      toasts.error(error.message);
    }
  });
  watch(
    () => filament.current?.id ?? null,
    (id) => {
      selected.value = id;
    },
    { immediate: true },
  );

  const chosen = computed(() => (selected.value === null ? null : filament.byId(selected.value)));
  const issues = computed(() => printIssues(metadata.value, chosen.value));
  const issuesFor = (spool) => printIssues(metadata.value, spool);
  const needed = computed(() => {
    const grams = gramsNeeded(metadata.value, chosen.value ?? filament.current);
    return grams != null ? formatFilament(grams, null) : formatFilament(null, metadata.value?.filament_mm);
  });
  const summary = computed(() =>
    [needed.value, metadata.value?.filament_type, formatDuration(metadata.value?.estimated_seconds)].filter((part) => part && part !== '–').join(' · '),
  );

  async function start() {
    busy.value = true;
    try {
      if (selected.value !== (filament.current?.id ?? null)) {
        if (chosen.value) await filament.loadSpool(chosen.value);
        else await filament.unloadSpool();
      }
      await files.print(file.value);
      printer.refreshSoon();
      toasts.success(`${file.value.name} started`);
      printStart.dismiss();
    } catch (error) {
      toasts.error(error.message);
    } finally {
      busy.value = false;
    }
  }

  return { printStart, filament, file, metadata, selected, chosen, issues, issuesFor, summary, busy, start };
}
