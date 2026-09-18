import { computed, onMounted } from 'vue';
import { usePrinterProfileStore } from '../stores/printerProfiles';
import { useSettingsStore } from '../stores/settings';

/** The bed of the configured printer profile for the 3D viewers; null until known or without a profile. */
export function usePrinterBed() {
  const settings = useSettingsStore();
  const profiles = usePrinterProfileStore();

  onMounted(async () => {
    try {
      await Promise.all([settings.loaded ? null : settings.load(), profiles.load()]);
    } catch {
      // Without a profile the viewer draws the grid around the model instead of the bed.
    }
  });

  return computed(() => {
    const profile = profiles.find(settings.values.printer_profile);
    return profile?.bed ? { ...profile.bed, centered: profile.type === 'delta' } : null;
  });
}
