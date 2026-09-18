import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useSettingsStore } from '../stores/settings';
import { isEnded, tabState } from '../tab/tabProgress';
import { restoreFavicon, showRing } from '../tab/favicon';

/**
 * Mirrors the print job into the browser tab: the title reads the percent or the activity and
 * the favicon wears a progress ring. A job that ends while the tab is hidden leaves its outcome
 * in the tab until the user looks at it; one that ends in view is left to the toast.
 */
export function useTabProgress(job) {
  const settings = useSettingsStore();
  const showEnding = ref(false);

  function onVisibility() {
    if (!document.hidden) showEnding.value = false;
  }

  onMounted(() => document.addEventListener('visibilitychange', onVisibility));
  onBeforeUnmount(() => {
    document.removeEventListener('visibilitychange', onVisibility);
    restoreFavicon();
    document.title = tabState(null).title;
  });

  watch(
    () => [job()?.id, job()?.state],
    ([id, state], [previousId, previousState]) => {
      if (id !== previousId) showEnding.value = false;
      if (id === previousId && isEnded(state) && !isEnded(previousState)) showEnding.value = document.hidden;
    },
  );

  let drawn = null;
  watch(
    () => tabState(settings.values.tab_progress === false ? null : job(), { showEnding: showEnding.value }),
    ({ title, ring }) => {
      document.title = title;
      if (!ring) {
        drawn = null;
        restoreFavicon();
        return;
      }
      // One frame per visible step: the poll arrives every 2 s, the ring moves once per percent.
      const key = `${ring.tone}:${Math.round(ring.fraction * 100)}`;
      if (key === drawn) return;
      drawn = key;
      showRing(ring.fraction, ring.tone).catch(() => {});
    },
    { immediate: true },
  );
}
