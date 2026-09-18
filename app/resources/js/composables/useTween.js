import { onBeforeUnmount, ref, watch } from 'vue';

/**
 * A number that eases toward `source` instead of jumping, for figures that
 * change with every poll. A null source is passed through unchanged.
 */
export function useTween(source, duration = 600) {
  const value = ref(source.value);
  let frame = null;

  watch(source, (target) => {
    cancelAnimationFrame(frame);
    if (target == null || value.value == null) {
      value.value = target;
      return;
    }
    const from = value.value;
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / duration);
      value.value = from + (target - from) * (1 - (1 - t) ** 3);
      if (t < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
  });

  onBeforeUnmount(() => cancelAnimationFrame(frame));
  return value;
}
