import { onBeforeUnmount, onMounted, ref } from 'vue';

/** A timestamp that ticks while the component is mounted, for clocks that count between polls. */
export function useNow(intervalMs = 1000) {
  const now = ref(Date.now());
  let timer = null;
  onMounted(() => {
    timer = setInterval(() => {
      now.value = Date.now();
    }, intervalMs);
  });
  onBeforeUnmount(() => clearInterval(timer));
  return now;
}
