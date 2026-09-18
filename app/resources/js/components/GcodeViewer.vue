<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
import {
  Box3,
  BufferAttribute,
  BufferGeometry,
  Color,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshBasicMaterial,
  PerspectiveCamera,
  Scene,
  SphereGeometry,
  Vector3,
  WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { FEATURES, TRAVEL_COLOR } from '../gcode/features';
import { segmentsUpToLine } from '../gcode/parse';
import { useGcodeModelStore } from '../stores/gcodeModels';
import { GRID_STEP, bedArea as profileArea, bedGrid, disposeObject, fitCamera, retint, themeColor } from '../three/scene';
import GcodeLayerSlider from './GcodeLayerSlider.vue';
import GcodeLegend from './GcodeLegend.vue';
import Icon from './Icon.vue';
import ProgressBar from './ProgressBar.vue';
import ToggleButton from './ToggleButton.vue';

/**
 * live: follow a running print instead of browsing layers. Everything up to
 * printedLine (a line number of the file) is drawn in full color, the rest as
 * a faint outline, and a marker sits where the nozzle is.
 */
const props = defineProps({
  file: { type: Object, required: true },
  bed: { type: Object, default: null }, // { x, y, z, centered }
  live: { type: Boolean, default: false },
  printedLine: { type: Number, default: null },
});
const emit = defineEmits(['loaded']);

const models = useGcodeModelStore();
const container = ref(null);
// The store downloads and parses once per file; this component only draws what it holds.
const entry = computed(() => models.entryFor(props.file));
const phase = computed(() => entry.value?.phase ?? 'loading');
const progress = computed(() => entry.value?.progress ?? 0);
const error = computed(() => entry.value?.error ?? null);
const model = shallowRef(null);
const layer = ref(0);
const showTravel = ref(false);
const showUpcoming = ref(true);
const legend = ref([]);

const layerCount = computed(() => model.value?.layerZ.length ?? 0);
const layerZ = computed(() => (model.value && layer.value > 0 ? model.value.layerZ[layer.value - 1] : null));

let renderer = null;
let scene = null;
let camera = null;
let controls = null;
let frame = 0;
let observer = null;
let extrusionLines = null;
let travelLines = null;
let upcomingLines = null;
let headMarker = null;
let bedGroup = null;

function setupScene() {
  renderer = new WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(themeColor('--color-zinc-950'));
  renderer.domElement.className = 'block size-full touch-none';
  container.value.appendChild(renderer.domElement);
  window.addEventListener('printpi:theme', onTheme);

  scene = new Scene();
  camera = new PerspectiveCamera(40, 1, 0.1, 5000);
  camera.up.set(0, 0, 1);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.12;
  controls.screenSpacePanning = true;
  controls.maxPolarAngle = Math.PI * 0.95;

  observer = new ResizeObserver(resize);
  observer.observe(container.value);
  resize();
  animate();
}

function resize() {
  const element = container.value;
  if (!element || !renderer) return;
  const { clientWidth: width, clientHeight: height } = element;
  if (!width || !height) return;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function onTheme() {
  renderer?.setClearColor(themeColor('--color-zinc-950'));
  if (scene) retint(scene);
}

function animate() {
  frame = requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

function buildModel(parsed) {
  model.value = parsed;
  const { extrusions, travels } = parsed;

  // Vertex colors are stored as linear-space bytes, one entry per feature type.
  const palette = FEATURES.map((feature) => {
    const color = new Color(feature.color);
    return [Math.round(color.r * 255), Math.round(color.g * 255), Math.round(color.b * 255)];
  });
  const colors = new Uint8Array(extrusions.count * 6);
  for (let index = 0; index < extrusions.count; index += 1) {
    const [r, g, b] = palette[extrusions.features[index]];
    const offset = index * 6;
    colors[offset] = r;
    colors[offset + 1] = g;
    colors[offset + 2] = b;
    colors[offset + 3] = r;
    colors[offset + 4] = g;
    colors[offset + 5] = b;
  }

  const extrusionGeometry = new BufferGeometry();
  extrusionGeometry.setAttribute('position', new BufferAttribute(extrusions.positions, 3));
  extrusionGeometry.setAttribute('color', new BufferAttribute(colors, 3, true));
  extrusionLines = new LineSegments(extrusionGeometry, new LineBasicMaterial({ vertexColors: true }));

  const travelGeometry = new BufferGeometry();
  travelGeometry.setAttribute('position', new BufferAttribute(travels.positions, 3));
  travelLines = new LineSegments(travelGeometry, new LineBasicMaterial({ color: TRAVEL_COLOR, transparent: true, opacity: 0.4 }));
  travelLines.visible = showTravel.value;

  scene.add(extrusionLines, travelLines);
  if (props.live) buildLiveObjects(parsed, extrusionGeometry);
  legend.value = FEATURES.filter((_, index) => parsed.featuresUsed[index]);
  layer.value = parsed.layerZ.length;
  if (props.live) applyProgress();
  else applyLayer();
  buildBed();
  fitView();
  emit('loaded', {
    layers: parsed.layerZ.length,
    size: parsed.bounds.max.map((value, axis) => value - parsed.bounds.min[axis]),
  });
}

/** The unprinted remainder shares the position buffer and only differs in draw range and material. */
function buildLiveObjects(parsed, extrusionGeometry) {
  const upcomingGeometry = new BufferGeometry();
  upcomingGeometry.setAttribute('position', extrusionGeometry.getAttribute('position'));
  upcomingLines = new LineSegments(upcomingGeometry, new LineBasicMaterial({ color: 0x71717a, transparent: true, opacity: 0.45 }));

  const size = new Vector3(...parsed.bounds.max).sub(new Vector3(...parsed.bounds.min)).length();
  headMarker = new Mesh(new SphereGeometry(Math.max(0.4, size * 0.004), 16, 12), new MeshBasicMaterial({ color: 0x34d399 }));
  headMarker.visible = false;
  scene.add(upcomingLines, headMarker);
}

function applyLayer() {
  const parsed = model.value;
  if (!parsed || !extrusionLines || props.live) return;
  const shown = layer.value;
  extrusionLines.geometry.setDrawRange(0, shown > 0 ? parsed.layerExtrusionEnd[shown - 1] * 2 : 0);
  travelLines.geometry.setDrawRange(0, shown > 0 ? parsed.layerTravelEnd[shown - 1] * 2 : 0);
}

function applyProgress() {
  const parsed = model.value;
  if (!parsed || !upcomingLines) return;
  const line = props.printedLine ?? 0;
  const printed = segmentsUpToLine(parsed.extrusions.lines, line);
  const travelled = segmentsUpToLine(parsed.travels.lines, line);
  extrusionLines.geometry.setDrawRange(0, printed * 2);
  upcomingLines.geometry.setDrawRange(printed * 2, (parsed.extrusions.count - printed) * 2);
  upcomingLines.visible = showUpcoming.value;
  travelLines.geometry.setDrawRange(0, travelled * 2);
  placeMarker(parsed, printed, travelled);
}

/** The nozzle sits at the end of the latest segment, whichever kind came last in the file. */
function placeMarker(parsed, printed, travelled) {
  const lastExtrusion = printed ? parsed.extrusions.lines[printed - 1] : -1;
  const lastTravel = travelled ? parsed.travels.lines[travelled - 1] : -1;
  if (lastExtrusion < 0 && lastTravel < 0) {
    headMarker.visible = false;
    return;
  }
  const [segments, index] = lastTravel > lastExtrusion ? [parsed.travels, travelled - 1] : [parsed.extrusions, printed - 1];
  const offset = index * 6 + 3;
  headMarker.position.set(segments.positions[offset], segments.positions[offset + 1], segments.positions[offset + 2]);
  headMarker.visible = true;
}

/** The printer's bed when a profile is known, otherwise the model footprint padded to the grid. */
function bedArea() {
  if (props.bed) return profileArea(props.bed);
  const parsed = model.value;
  if (!parsed || !parsed.extrusions.count) return null;
  const [x0, y0] = parsed.bounds.min;
  const [x1, y1] = parsed.bounds.max;
  const minX = Math.floor((x0 - GRID_STEP) / GRID_STEP) * GRID_STEP;
  const minY = Math.floor((y0 - GRID_STEP) / GRID_STEP) * GRID_STEP;
  return {
    minX,
    minY,
    sizeX: Math.ceil((x1 + GRID_STEP) / GRID_STEP) * GRID_STEP - minX,
    sizeY: Math.ceil((y1 + GRID_STEP) / GRID_STEP) * GRID_STEP - minY,
  };
}

function buildBed() {
  if (!scene) return;
  if (bedGroup) {
    scene.remove(bedGroup);
    disposeObject(bedGroup);
    bedGroup = null;
  }
  const area = bedArea();
  if (!area) return;
  bedGroup = bedGrid(area);
  scene.add(bedGroup);
}

function fitView() {
  if (!camera) return;
  const parsed = model.value;
  const box = new Box3();
  if (parsed && parsed.extrusions.count) {
    box.set(new Vector3(...parsed.bounds.min), new Vector3(...parsed.bounds.max));
  } else {
    const area = bedArea();
    if (!area) return;
    box.set(new Vector3(area.minX, area.minY, 0), new Vector3(area.minX + area.sizeX, area.minY + area.sizeY, 0));
  }
  fitCamera(camera, controls, box);
}

function dispose() {
  cancelAnimationFrame(frame);
  window.removeEventListener('printpi:theme', onTheme);
  observer?.disconnect();
  controls?.dispose();
  if (scene) disposeObject(scene);
  renderer?.dispose();
  renderer?.domElement.remove();
}

watch(layer, applyLayer);
watch(showTravel, (visible) => {
  if (travelLines) travelLines.visible = visible;
});
watch(() => props.printedLine, applyProgress);
watch(showUpcoming, applyProgress);
watch(() => props.bed, buildBed, { deep: true });

onMounted(() => {
  setupScene();
  watch(() => props.file, (file) => models.load(file), { immediate: true });
  watch(
    () => entry.value?.model,
    (parsed) => {
      if (parsed && parsed !== model.value) buildModel(parsed);
    },
    { immediate: true },
  );
});
onBeforeUnmount(dispose);
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex flex-wrap items-center gap-3 border-b border-zinc-800 px-4 py-2">
      <GcodeLayerSlider v-if="!live" v-model="layer" :count="layerCount" :z="layerZ" class="min-w-56 flex-1" />
      <ToggleButton v-if="live" v-model="showUpcoming">Upcoming</ToggleButton>
      <ToggleButton v-model="showTravel">Travel moves</ToggleButton>
      <button
        type="button"
        class="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
        title="Reset view"
        @click="fitView"
      >
        <Icon name="expand" />
      </button>
    </div>
    <div ref="container" class="relative min-h-0 flex-1 bg-zinc-950">
      <div v-if="phase !== 'ready'" class="absolute inset-0 flex flex-col items-center justify-center gap-3 text-sm text-zinc-300">
        <template v-if="phase === 'error'">
          <Icon name="warning" class="size-6 text-red-400" />
          <span>{{ error }}</span>
        </template>
        <template v-else>
          <span class="tabular-nums">{{ phase === 'loading' ? `Loading … ${Math.round(progress * 100)} %` : 'Parsing …' }}</span>
          <ProgressBar :value="phase === 'loading' ? progress : null" />
        </template>
      </div>
      <GcodeLegend v-if="legend.length" :features="legend" class="pointer-events-none absolute bottom-3 left-3 right-3" />
    </div>
  </div>
</template>
