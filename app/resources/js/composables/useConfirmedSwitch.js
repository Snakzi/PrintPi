import { computed, onBeforeUnmount, ref, watch } from 'vue';

/**
 * A switch whose state a plugin confirms with the next poll: `on` shows the requested state
 * until the reported one matches it or `timeout` ms pass. `reported` reads the plugin's
 * value, `request` sends the change and may throw.
 */
export function useConfirmedSwitch(reported, request, timeout = 8000) {
  const requested = ref(null);
  const error = ref(null);
  let timer = null;

  function settle() {
    clearTimeout(timer);
    requested.value = null;
  }

  watch(reported, (on) => {
    if (requested.value !== null && on === requested.value) settle();
  });
  onBeforeUnmount(() => clearTimeout(timer));

  const on = computed(() => requested.value ?? Boolean(reported()));
  const pending = computed(() => requested.value !== null);

  async function toggle() {
    const next = !on.value;
    requested.value = next;
    error.value = null;
    clearTimeout(timer);
    timer = setTimeout(settle, timeout);
    try {
      await request(next);
    } catch (e) {
      settle();
      error.value = e;
      throw e;
    }
  }

  return { on, pending, toggle };
}
