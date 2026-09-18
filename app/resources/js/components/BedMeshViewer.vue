<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import {
  AmbientLight,
  Box3,
  BufferAttribute,
  BufferGeometry,
  Color,
  DirectionalLight,
  DoubleSide,
  Group,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshBasicMaterial,
  MeshLambertMaterial,
  PerspectiveCamera,
  PlaneGeometry,
  Points,
  PointsMaterial,
  Raycaster,
  Scene,
  SphereGeometry,
  SRGBColorSpace,
  Vector2,
  Vector3,
  WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { deviationColor, formatMm, meshPositions, meshStats } from '../bedmesh';
import { bedArea, bedGrid, disposeObject, fitCamera, retint, themeColor, themed } from '../three/scene';
import BedMeshLegend from './BedMeshLegend.vue';
import Icon from './Icon.vue';

const props = defineProps({
  mesh: { type: Object, required: true }, // { rows, cols, z, x, y }
  tolerance: { type: Number, default: 0.1 },
  bed: { type: Object, default: null }, // { x, y, centered } from the printer profile
});

const container = ref(null);
const hover = ref(null);

// Heights are exaggerated: one tolerance reads as this share of the bed size, capped so a
// badly tilted bed still fits the view.
const TOLERANCE_HEIGHT = 0.08;
const MAX_HEIGHT = 0.25;
const FALLBACK_AREA = { minX: 0, minY: 0, sizeX: 200, sizeY: 200 };

let renderer = null;
let scene = null;
let camera = null;
let controls = null;
let frame = 0;
let observer = null;
let model = null;
let surface = null;
let marker = null;
let area = null;
let positions = null;
let known = false;
const raycaster = new Raycaster();
const pointer = new Vector2();

// The store hands over a fresh object with every poll; only a changed mesh rebuilds the scene.
const signature = computed(() => JSON.stringify([props.mesh.z, props.mesh.x, props.mesh.y, props.tolerance, props.bed]));

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

  const sun = new DirectionalLight(0xffffff, 2.0);
  sun.position.set(0.5, -1, 1.5);
  scene.add(new AmbientLight(0xffffff, 1.5), sun);

  marker = new Mesh(new SphereGeometry(1, 12, 12), new MeshBasicMaterial({ color: 0xfafafa }));
  marker.visible = false;
  scene.add(marker);

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

function modelArea(mesh) {
  const profile = bedArea(props.bed);
  if (profile) return profile;
  if (mesh.x && mesh.y) {
    const [minX, maxX] = [Math.min(...mesh.x), Math.max(...mesh.x)];
    const [minY, maxY] = [Math.min(...mesh.y), Math.max(...mesh.y)];
    return { minX, minY, sizeX: maxX - minX, sizeY: maxY - minY };
  }
  return FALLBACK_AREA;
}

function clearModel() {
  if (!model) return;
  scene.remove(model);
  disposeObject(model);
  model = null;
  surface = null;
  leave();
}

function build(refit) {
  clearModel();
  const { mesh, tolerance } = props;
  const stats = meshStats(mesh);
  if (!stats) return;
  area = modelArea(mesh);
  known = Boolean(mesh.x && mesh.y) || Boolean(props.bed);
  positions = meshPositions(mesh, area);
  const size = Math.max(area.sizeX, area.sizeY);
  const maxAbs = Math.max(stats.max - stats.mean, stats.mean - stats.min, 1e-6);
  const zScale = Math.min((TOLERANCE_HEIGHT * size) / tolerance, (MAX_HEIGHT * size) / maxAbs);

  const { rows, cols, z } = mesh;
  const vertices = new Float32Array(rows * cols * 3);
  const colors = new Float32Array(rows * cols * 3);
  const probed = [];
  const probedColors = [];
  const color = new Color();
  const valid = (row, col) => z[row]?.[col] != null;
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const index = row * cols + col;
      const delta = valid(row, col) ? z[row][col] - stats.mean : 0;
      const [r, g, b] = deviationColor(delta, tolerance);
      color.setRGB(r / 255, g / 255, b / 255, SRGBColorSpace);
      vertices.set([positions.x[col], positions.y[row], delta * zScale], index * 3);
      colors.set([color.r, color.g, color.b], index * 3);
      if (valid(row, col)) {
        probed.push(positions.x[col], positions.y[row], delta * zScale);
        probedColors.push(color.r, color.g, color.b);
      }
    }
  }
  const triangles = [];
  const edges = [];
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const index = row * cols + col;
      if (!valid(row, col)) continue;
      if (col + 1 < cols && valid(row, col + 1)) edges.push(index, index + 1);
      if (row + 1 < rows && valid(row + 1, col)) edges.push(index, index + cols);
      if (col + 1 < cols && row + 1 < rows && valid(row, col + 1) && valid(row + 1, col) && valid(row + 1, col + 1)) {
        triangles.push(index, index + 1, index + cols + 1, index, index + cols + 1, index + cols);
      }
    }
  }

  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(vertices, 3));
  geometry.setAttribute('color', new BufferAttribute(colors, 3));
  geometry.setIndex(triangles);
  geometry.computeVertexNormals();
  surface = new Mesh(
    geometry,
    new MeshLambertMaterial({ vertexColors: true, side: DoubleSide, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 }),
  );

  const wire = new BufferGeometry();
  wire.setAttribute('position', new BufferAttribute(vertices, 3));
  wire.setIndex(edges);
  const wireframe = new LineSegments(wire, new LineBasicMaterial({ color: 0x09090b, transparent: true, opacity: 0.35 }));

  // UBL fills its whole grid from far fewer probes; a fully populated UBL report says nothing
  // about which points were measured, so it gets no dots.
  const interpolated = String(mesh.format ?? '').startsWith('ubl') && probed.length === rows * cols * 3;
  const dots = new BufferGeometry();
  dots.setAttribute('position', new BufferAttribute(Float32Array.from(probed), 3));
  dots.setAttribute('color', new BufferAttribute(Float32Array.from(probedColors), 3));
  const points = new Points(dots, new PointsMaterial({ vertexColors: true, size: 5, sizeAttenuation: false }));
  points.visible = !interpolated;

  // The mean plane, so it is visible where the surface dips below it.
  const plane = new Mesh(
    new PlaneGeometry(area.sizeX, area.sizeY),
    themed(new MeshBasicMaterial({ transparent: true, opacity: 0.18, side: DoubleSide, depthWrite: false }), '--color-zinc-600'),
  );
  plane.position.set(area.minX + area.sizeX / 2, area.minY + area.sizeY / 2, 0);

  marker.scale.setScalar(size * 0.012);
  model = new Group();
  model.add(bedGrid(area), plane, surface, wireframe, points);
  scene.add(model);
  if (refit) fitView();
}

function fitView() {
  if (!camera || !model) return;
  fitCamera(camera, controls, new Box3().setFromObject(model), { padding: 0.8 });
}

function onPointerMove(event) {
  if (!surface) return;
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.set(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  const [hit] = raycaster.intersectObject(surface);
  if (!hit) {
    leave();
    return;
  }
  const attribute = surface.geometry.getAttribute('position');
  const corner = new Vector3();
  let nearest = hit.face.a;
  let best = Infinity;
  for (const index of [hit.face.a, hit.face.b, hit.face.c]) {
    const distance = corner.fromBufferAttribute(attribute, index).distanceTo(hit.point);
    if (distance < best) {
      best = distance;
      nearest = index;
    }
  }
  const row = Math.floor(nearest / props.mesh.cols);
  const col = nearest % props.mesh.cols;
  marker.position.fromBufferAttribute(attribute, nearest);
  marker.visible = true;
  hover.value = {
    place: known ? `X ${Math.round(positions.x[col])} · Y ${Math.round(positions.y[row])}` : `Column ${col} · Row ${row}`,
    z: props.mesh.z[row][col],
    left: event.clientX - rect.left,
    top: event.clientY - rect.top,
  };
}

function leave() {
  hover.value = null;
  if (marker) marker.visible = false;
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

watch(signature, () => build(false));

onMounted(() => {
  setupScene();
  build(true);
});
onBeforeUnmount(dispose);
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex items-center gap-3 border-b border-zinc-800 px-4 py-2">
      <BedMeshLegend :tolerance="tolerance" class="flex-1" />
      <button
        type="button"
        class="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
        title="Reset view"
        @click="fitView"
      >
        <Icon name="expand" />
      </button>
    </div>
    <div ref="container" class="relative min-h-0 flex-1 bg-zinc-950" @pointermove="onPointerMove" @pointerleave="leave">
      <div
        v-if="hover"
        class="pointer-events-none absolute z-10 flex gap-2 rounded-md border border-zinc-700 bg-zinc-900/95 px-2 py-1 text-xs tabular-nums shadow-lg"
        :style="{ left: `${hover.left + 14}px`, top: `${hover.top + 14}px` }"
      >
        <span class="text-zinc-400">{{ hover.place }}</span>
        <span class="font-medium text-zinc-100">{{ formatMm(hover.z) }} mm</span>
      </div>
    </div>
  </div>
</template>
