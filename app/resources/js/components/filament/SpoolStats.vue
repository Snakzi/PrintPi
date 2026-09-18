<script setup>
import { computed } from 'vue';
import { useFilamentStore } from '../../stores/filament';
import { formatLength, formatWeight } from '../../format';
import StatTile from '../StatTile.vue';

/* The inventory in figures: spools in use, their materials and what is left on them altogether. */
const filament = useFilamentStore();

const spools = computed(() => filament.active);
const materials = computed(() => [...new Set(spools.value.map((spool) => spool.material).filter(Boolean))]);
const grams = computed(() => spools.value.reduce((sum, spool) => sum + (spool.remaining ?? 0), 0));
const millimetres = computed(() => spools.value.reduce((sum, spool) => sum + (spool.remaining_mm ?? 0), 0));
</script>

<template>
  <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
    <StatTile label="Spools" :value="spools.length">
      <template v-if="filament.archived.length" #footer>
        <span class="text-xs text-zinc-500">{{ filament.archived.length }} archived</span>
      </template>
    </StatTile>
    <StatTile label="Materials" :value="materials.length">
      <template v-if="materials.length" #footer>
        <span class="truncate text-xs text-zinc-500" :title="materials.join(', ')">{{ materials.join(', ') }}</span>
      </template>
    </StatTile>
    <StatTile label="Filament left" :value="formatWeight(grams)" />
    <StatTile label="Length" :value="formatLength(millimetres)" />
  </div>
</template>
