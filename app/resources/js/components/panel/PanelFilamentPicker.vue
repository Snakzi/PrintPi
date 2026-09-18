<script setup>
import { computed, onMounted, ref } from 'vue';
import { useFilamentStore } from '../../stores/filament';
import { useFilamentChangeStore } from '../../stores/filamentChange';
import { useToastStore } from '../../stores/toasts';
import PanelButton from './PanelButton.vue';
import PanelChips from './PanelChips.vue';
import PanelSpoolTile from './PanelSpoolTile.vue';
import PanelSwitch from './PanelSwitch.vue';

/* Which filament goes in: a spool of the inventory as tiles, or a bare material for one that is
   not in it. "Unload first" makes it a change; it is on whenever a spool is loaded. */
const emit = defineEmits(['close']);

const filament = useFilamentStore();
const change = useFilamentChangeStore();
const toasts = useToastStore();

const MATERIALS = ['PLA', 'PETG', 'ABS', 'ASA', 'TPU', 'PC', 'PA', 'PVA'];
const OTHER = 'other';

const selected = ref(null);
const material = ref('PLA');
const unloadFirst = ref(Boolean(filament.current));

onMounted(async () => {
  try {
    await filament.ensure();
  } catch (error) {
    toasts.error(error.message);
  }
});

const spools = computed(() => filament.active.filter((spool) => !spool.loaded));
const materials = MATERIALS.map((value) => ({ value, label: value }));
const ready = computed(() => selected.value !== null && !change.busy);

async function start() {
  try {
    if (selected.value === OTHER) await change.load({ material: material.value, unloadFirst: unloadFirst.value });
    else await change.load({ spoolId: selected.value, unloadFirst: unloadFirst.value });
    emit('close');
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <div class="flex h-full flex-col gap-3">
    <div class="flex shrink-0 items-center justify-between gap-3">
      <div class="text-xl font-semibold">Load filament</div>
      <PanelSwitch icon="arrow-up" label="Unload first" :on="unloadFirst" @click="unloadFirst = !unloadFirst" />
    </div>

    <div role="radiogroup" aria-label="Filament" class="grid min-h-0 flex-1 auto-rows-max grid-cols-2 gap-3 overflow-y-auto overscroll-contain pr-1" style="touch-action: pan-y">
      <PanelSpoolTile v-for="spool in spools" :key="spool.id" :spool="spool" :selected="selected === spool.id" @select="selected = spool.id" />
      <button
        type="button"
        role="radio"
        :aria-checked="selected === OTHER"
        class="flex min-h-24 w-full items-center rounded-2xl border-2 p-4 text-left text-lg font-medium transition-colors"
        :class="selected === OTHER ? 'border-emerald-500 bg-emerald-500/10 text-zinc-100' : 'border-dashed border-zinc-700 text-zinc-400 active:bg-zinc-900'"
        @click="selected = OTHER"
      >
        {{ selected === OTHER ? material : 'Other material' }}
      </button>
    </div>

    <PanelChips v-if="selected === OTHER" v-model="material" :options="materials" class="shrink-0 self-start" />

    <div class="grid shrink-0 grid-cols-2 gap-3">
      <PanelButton icon="x" @click="emit('close')">Cancel</PanelButton>
      <PanelButton variant="primary" icon="arrow-down" :disabled="!ready" @click="start">{{ unloadFirst ? 'Change' : 'Load' }}</PanelButton>
    </div>
  </div>
</template>
