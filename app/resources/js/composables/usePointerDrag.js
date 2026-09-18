/* Turns a pointer press and drag over an element into positions in 0–1 of its box, from the first
   press to release, with the pointer captured so the drag survives leaving the element. Returns the
   handlers to bind: pointerdown, pointermove, pointerup and pointercancel. */
export function usePointerDrag(target, onPoint, { disabled = () => false } = {}) {
  const clamp = (value) => Math.min(1, Math.max(0, value));

  function report(event) {
    const rect = target.value.getBoundingClientRect();
    onPoint({
      x: rect.width ? clamp((event.clientX - rect.left) / rect.width) : 0,
      y: rect.height ? clamp((event.clientY - rect.top) / rect.height) : 0,
    });
  }

  function onPointerDown(event) {
    if (disabled() || !target.value || (event.pointerType === 'mouse' && event.button !== 0)) return;
    event.preventDefault();
    target.value.focus?.({ preventScroll: true });
    target.value.setPointerCapture(event.pointerId);
    report(event);
  }

  function onPointerMove(event) {
    if (target.value?.hasPointerCapture(event.pointerId)) report(event);
  }

  function onPointerUp(event) {
    if (target.value?.hasPointerCapture(event.pointerId)) target.value.releasePointerCapture(event.pointerId);
  }

  return { onPointerDown, onPointerMove, onPointerUp };
}
