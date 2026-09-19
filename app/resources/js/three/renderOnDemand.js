/** Coalesce scene changes into one frame; keep drawing only while controls are moving. */
export function renderOnDemand(draw, {
  requestFrame = requestAnimationFrame,
  cancelFrame = cancelAnimationFrame,
} = {}) {
  let frame = null;
  let visible = false;
  let disposed = false;

  function request() {
    if (disposed || !visible || frame !== null) return;
    frame = requestFrame(() => {
      frame = null;
      if (draw()) request();
    });
  }

  function cancel() {
    if (frame !== null) cancelFrame(frame);
    frame = null;
  }

  return {
    request,
    setVisible(value) {
      if (visible === value) return;
      visible = value;
      if (visible) request();
      else cancel();
    },
    dispose() {
      disposed = true;
      cancel();
    },
  };
}
