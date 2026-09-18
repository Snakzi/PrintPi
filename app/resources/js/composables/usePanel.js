import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

/* The panel under a split button: shown while the pointer hovers the root or after a tap on the
   chevron, closed by a click outside or Escape. `pin` keeps it open through a drag inside it, which
   pointer capture would otherwise let end as the mouse leaving the root. The panel hangs from the
   button's right edge unless it would leave the viewport there, as on a phone where the status bar
   wraps and the button sits at the left; `align` says which edge, measured whenever it opens. */
export function usePanel() {
  const root = ref(null);
  const panel = ref(null);
  const open = ref(false);
  const hovering = ref(false);
  const align = ref('right');
  const visible = computed(() => open.value || hovering.value);

  function measure() {
    if (!visible.value || !root.value || !panel.value) return;
    const rect = root.value.getBoundingClientRect();
    align.value = rect.right - panel.value.offsetWidth < 8 ? 'left' : 'right';
  }

  watch(visible, async (shown) => {
    if (!shown) return;
    await nextTick();
    measure();
  });

  function toggle() {
    open.value = !open.value;
  }

  function pin() {
    open.value = true;
  }

  function close() {
    open.value = false;
    hovering.value = false;
  }

  function onPointerDown(event) {
    if (open.value && root.value && !root.value.contains(event.target)) open.value = false;
  }

  function onKeydown(event) {
    if (event.key === 'Escape' && visible.value) close();
  }

  onMounted(() => {
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeydown);
    window.addEventListener('resize', measure);
  });
  onBeforeUnmount(() => {
    document.removeEventListener('pointerdown', onPointerDown);
    document.removeEventListener('keydown', onKeydown);
    window.removeEventListener('resize', measure);
  });

  return { root, panel, open, hovering, visible, align, toggle, pin, close };
}
