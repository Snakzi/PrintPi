<script setup>
import { computed } from 'vue';
import { cssColor, deviationColor, formatMm, meshPositions, meshStats } from '../bedmesh';
import { bedArea } from '../three/scene';

const props = defineProps({
  mesh: { type: Object, required: true }, // { rows, cols, z, x, y }
  tolerance: { type: Number, default: 0.1 },
  bed: { type: Object, default: null }, // { x, y, centered } from the printer profile
});

const stats = computed(() => meshStats(props.mesh));
// Positions in mm when the report or the printer profile says where the points are.
const known = computed(() => Boolean(props.mesh.x && props.mesh.y) || Boolean(props.bed));
const positions = computed(() => meshPositions(props.mesh, bedArea(props.bed)));
// The back of the bed is the top row, like looking at the printer from the front.
const rows = computed(() => [...props.mesh.z.keys()].reverse());

const label = (axis, index) => (known.value ? Math.round(positions.value[axis][index]) : index);

function cellStyle(value) {
  if (value == null || !stats.value) return {};
  return { backgroundColor: cssColor(deviationColor(value - stats.value.mean, props.tolerance), 0.3) };
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-xs tabular-nums">
      <thead>
        <tr class="text-zinc-500">
          <th class="px-1.5 py-1 text-left font-normal">{{ known ? 'Y \ X' : '' }}</th>
          <th v-for="col in mesh.cols" :key="col" class="px-1.5 py-1 text-center font-normal">{{ label('x', col - 1) }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row">
          <th class="px-1.5 py-0.5 text-left font-normal text-zinc-500">{{ label('y', row) }}</th>
          <td v-for="(value, col) in mesh.z[row]" :key="col" class="px-1.5 py-0.5 text-center text-zinc-100" :style="cellStyle(value)">
            {{ formatMm(value) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
