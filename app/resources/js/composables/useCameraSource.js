import { computed, onMounted, ref } from 'vue';
import { useCameraStore } from '../stores/camera';

/**
 * The URL of the camera picture for a view that only shows it: the daemon's own stream while
 * ustreamer runs on the chosen device, else the configured stream URL. `snapshot` is the
 * daemon's still-frame URL in the first case, for views that refresh a picture instead of
 * decoding the stream. `reload` gives the MJPEG stream a fresh query string so the browser
 * reopens it instead of reusing a stalled one.
 */
export function useCameraSource() {
  const camera = useCameraStore();
  const nonce = ref(Date.now());

  onMounted(async () => {
    if (!camera.loaded) await camera.load().catch(() => {});
  });

  const usbActive = computed(
    () => camera.settings.camera_device && camera.status.running && camera.status.device === camera.settings.camera_device,
  );
  const base = computed(() => (usbActive.value ? camera.streamUrl : camera.settings.camera_url) || null);
  const src = computed(() => (base.value ? `${base.value}${base.value.includes('?') ? '&' : '?'}_=${nonce.value}` : null));
  const snapshot = computed(() => (usbActive.value ? camera.snapshotUrl : null));

  function reload() {
    nonce.value = Date.now();
  }

  return { camera, src, snapshot, reload };
}
