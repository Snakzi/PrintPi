import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

/** Expensive widgets only work while their element and the browser tab are visible. */
export function useVisible(element) {
  const inViewport = ref(false);
  const tabVisible = ref(!document.hidden);
  let observer = null;
  const onVisibility = () => (tabVisible.value = !document.hidden);

  onMounted(() => {
    onVisibility();
    document.addEventListener('visibilitychange', onVisibility);
    observer = new IntersectionObserver(([entry]) => {
      inViewport.value = entry.isIntersecting;
    });
    watch(element, (target) => {
      observer.disconnect();
      inViewport.value = false;
      if (target) observer.observe(target);
    }, { immediate: true, flush: 'post' });
  });

  onBeforeUnmount(() => {
    observer?.disconnect();
    document.removeEventListener('visibilitychange', onVisibility);
  });

  return computed(() => inViewport.value && tabVisible.value);
}
