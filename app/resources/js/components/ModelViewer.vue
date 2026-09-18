<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
import {
  Box3,
  DirectionalLight,
  HemisphereLight,
  InstancedBufferAttribute,
  InstancedMesh,
  Mesh,
  MeshStandardMaterial,
  PCFSoftShadowMap,
  PerspectiveCamera,
  PlaneGeometry,
  Scene,
  ShadowMaterial,
  Vector3,
  WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { extrusionBoxes } from '../gcode/extrusionBoxes';
import { useGcodeModelStore } from '../stores/gcodeModels';
import { disposeObject, fitCamera } from '../three/scene';
import { strandGeometry } from '../three/strand';
import Icon from './Icon.vue';
import Spinner from './Spinner.vue';

/**
 * The printed part alone on a transparent canvas: every extrusion drawn as a lit strand in the
 * filament colour, its shadow on an invisible floor. Drag turns it, wheel or pinch zooms, and
 * there is nothing else. A spinner stands in until the model is parsed. With `still` the part
 * is drawn once, kept as a picture and the WebGL context is given up, for a screen that only
 * looks at it (the Pi's touch panel, where a live canvas of thousands of strands stutters).
 */
const props = defineProps({
  file: { type: Object, required: true },
  color: { type: String, default: '#a1a1aa' },
  still: { type: Boolean, default: false },
});

// A product-shot angle: from the front right, a little above the part.
const VIEW = new Vector3(0.9, -1, 0.55).normalize();
const LIGHT = new Vector3(-0.5, -0.7, 1.1).normalize();

const models = useGcodeModelStore();
const container = ref(null);
const entry = computed(() => models.entryFor(props.file));
const ready = ref(false);
const failed = ref(false);
const model = shallowRef(null);
const snapshot = ref(null);

let renderer = null;
let scene = null;
let camera = null;
let controls = null;
let observer = null;
let light = null;
let floor = null;
let part = null;
let frame = 0;
let animating = false;
let interacting = false;

function setupScene() {
  renderer = new WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance', preserveDrawingBuffer: props.still });
  renderer.setClearColor(0x000000, 0);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFSoftShadowMap;
  renderer.domElement.className = 'block size-full cursor-grab touch-none active:cursor-grabbing';
  container.value.appendChild(renderer.domElement);

  scene = new Scene();
  camera = new PerspectiveCamera(32, 1, 0.1, 5000);
  camera.up.set(0, 0, 1);

  scene.add(new HemisphereLight(0xffffff, 0x3f3f46, 1.6));
  light = new DirectionalLight(0xffffff, 2.4);
  light.castShadow = true;
  light.shadow.mapSize.set(2048, 2048);
  light.shadow.bias = -0.0004;
  light.shadow.normalBias = 0.06;
  scene.add(light, light.target);

  if (props.still) {
    observer = new ResizeObserver(resize);
    observer.observe(container.value);
    resize();
    return;
  }

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.1;
  controls.enablePan = false;
  controls.rotateSpeed = 0.8;
  controls.maxPolarAngle = Math.PI / 2 + 0.03;
  controls.addEventListener('start', () => {
    interacting = true;
    wake();
  });
  controls.addEventListener('end', () => {
    interacting = false;
    wake();
  });
  controls.addEventListener('change', wake);

  observer = new ResizeObserver(resize);
  observer.observe(container.value);
  resize();
}

function resize() {
  const element = container.value;
  if (!element || !renderer) return;
  const { clientWidth: width, clientHeight: height } = element;
  if (!width || !height) return;
  // Thousands of strands in a small box alias into grain; drawing at up to four times the
  // device resolution and letting the browser scale that down smooths the surface.
  renderer.setPixelRatio(Math.max(1, Math.min(window.devicePixelRatio * 2, 4, 2048 / Math.max(width, height))));
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  render();
}

function render() {
  if (!renderer || !part) return;
  renderer.render(scene, camera);
  if (props.still) freeze();
}

// The picture replaces the canvas once the part has been drawn at a real size; the scene goes with it.
function freeze() {
  const { width, height } = renderer.domElement;
  if (!width || !height) return;
  snapshot.value = renderer.domElement.toDataURL('image/png');
  dispose();
  renderer = null;
}

// Frames are only drawn while the view moves; a still part costs nothing.
function wake() {
  if (animating) return;
  animating = true;
  frame = requestAnimationFrame(step);
}

function step() {
  const moved = controls.update();
  render();
  if (moved || interacting) {
    frame = requestAnimationFrame(step);
  } else {
    animating = false;
  }
}

function buildPart(parsed) {
  clearPart();
  model.value = parsed;
  const { count, matrices, bounds } = extrusionBoxes(parsed);
  if (!count) {
    failed.value = true;
    return;
  }

  part = new InstancedMesh(strandGeometry(), new MeshStandardMaterial({ color: props.color, roughness: 0.65, metalness: 0 }), count);
  part.instanceMatrix = new InstancedBufferAttribute(matrices, 16);
  part.castShadow = true;
  part.receiveShadow = true;
  part.computeBoundingSphere();

  const box = new Box3(new Vector3(...bounds.min), new Vector3(...bounds.max));
  const center = box.getCenter(new Vector3());
  const radius = Math.max(box.getSize(new Vector3()).length() / 2, 5);

  floor = new Mesh(new PlaneGeometry(radius * 6, radius * 6), new ShadowMaterial({ opacity: 0.45 }));
  floor.position.set(center.x, center.y, 0);
  floor.receiveShadow = true;

  light.position.copy(center).addScaledVector(LIGHT, radius * 3);
  light.target.position.copy(center);
  const shadow = light.shadow.camera;
  shadow.left = shadow.bottom = -radius * 1.3;
  shadow.right = shadow.top = radius * 1.3;
  shadow.near = radius;
  shadow.far = radius * 5;
  shadow.updateProjectionMatrix();

  scene.add(part, floor);
  fitCamera(camera, controls, box, { direction: VIEW, padding: 1.0 });
  if (controls) {
    const distance = camera.position.distanceTo(controls.target);
    controls.minDistance = distance * 0.3;
    controls.maxDistance = distance * 3;
  }
  ready.value = true;
  render();
}

function clearPart() {
  for (const object of [part, floor]) {
    if (!object) continue;
    scene.remove(object);
    disposeObject(object);
  }
  part = floor = null;
  ready.value = false;
}

function dispose() {
  cancelAnimationFrame(frame);
  observer?.disconnect();
  controls?.dispose();
  if (scene) disposeObject(scene);
  renderer?.dispose();
  renderer?.domElement.remove();
  observer = controls = scene = part = floor = null;
}

onMounted(() => {
  setupScene();
  watch(() => props.file, (file) => models.load(file), { immediate: true });
  watch(
    () => entry.value?.model,
    (parsed) => {
      if (parsed && parsed !== model.value) buildPart(parsed);
    },
    { immediate: true },
  );
  watch(
    () => entry.value?.phase,
    (phase) => (failed.value = phase === 'error'),
    { immediate: true },
  );
  watch(
    () => props.color,
    (color) => {
      if (snapshot.value) {
        // The picture is in the old colour; draw the part again for the new one.
        snapshot.value = null;
        setupScene();
        if (model.value) buildPart(model.value);
        return;
      }
      if (!part) return;
      part.material.color.set(color);
      render();
    },
  );
});
onBeforeUnmount(dispose);
</script>

<template>
  <div ref="container" class="relative size-full overflow-hidden">
    <img v-if="snapshot" :src="snapshot" alt="" class="pointer-events-none size-full object-contain">
    <div v-if="!ready" class="pointer-events-none absolute inset-0 flex items-center justify-center">
      <Icon v-if="failed" name="cube" class="size-8 text-zinc-700" />
      <Spinner v-else size="size-8" />
    </div>
  </div>
</template>
