<script setup>
import { computed, ref } from 'vue';
import { useFilamentStore } from '../../stores/filament';
import { useFilamentChangeStore } from '../../stores/filamentChange';
import { useToastStore } from '../../stores/toasts';
import AppButton from '../AppButton.vue';
import ToggleButton from '../ToggleButton.vue';
import PaletteModal from './PaletteModal.vue';
import SpoolFormModal from './SpoolFormModal.vue';
import { useConfirm } from '../../composables/useConfirm';
import SpoolRow from './SpoolRow.vue';
import SpoolWeighModal from './SpoolWeighModal.vue';

/* The inventory as a table with the loaded spool on top; archived spools are shown on request.
   With a connected, idle printer the load and unload buttons run the filament walkthrough and the
   inventory follows the printer; otherwise they only book which spool is in. */
const filament = useFilamentStore();
const change = useFilamentChangeStore();
const toasts = useToastStore();
const confirm = useConfirm();

const showArchived = ref(false);
const editing = ref(null);
const creating = ref(false);
const weighing = ref(null);
const sharing = ref(false);

const rows = computed(() => (showArchived.value ? filament.items : filament.active));

async function run(action, message = null) {
  try {
    await action();
    if (message) toasts.success(message);
  } catch (error) {
    toasts.error(error.message);
  }
}

function loadSpool(spool) {
  if (change.available) return run(() => change.load({ spoolId: spool.id, unloadFirst: Boolean(filament.current) }));
  return run(() => filament.loadSpool(spool), `${spool.name} loaded`);
}

function unloadSpool(spool) {
  if (change.available) return run(() => change.unload());
  return run(() => filament.unloadSpool(), `${spool.name} unloaded`);
}

async function remove(spool) {
  if (!(await confirm(`Delete ${spool.name}?`, { message: 'Its prints stay in the history without a spool.', danger: true }))) return;
  run(() => filament.remove(spool), `${spool.name} deleted`);
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <ToggleButton v-model="showArchived" :disabled="!filament.archived.length">Archived ({{ filament.archived.length }})</ToggleButton>
      <div class="flex items-center gap-2">
        <AppButton icon="photo" :disabled="!filament.active.length" @click="sharing = true">Colour card</AppButton>
        <AppButton variant="primary" icon="plus" @click="creating = true">Add spool</AppButton>
      </div>
    </div>

    <div class="overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-900">
      <table class="w-full text-left text-sm">
        <thead class="text-xs tracking-wide text-zinc-500 uppercase">
          <tr>
            <th class="px-4 py-3 font-medium">Spool</th>
            <th class="hidden px-4 py-3 font-medium lg:table-cell">Diameter</th>
            <th class="px-4 py-3 font-medium">Remaining</th>
            <th class="hidden px-4 py-3 font-medium xl:table-cell">Weight</th>
            <th class="hidden px-4 py-3 font-medium xl:table-cell">Added</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-if="filament.loading && !filament.items.length">
            <td colspan="6" class="px-4 py-6 text-center text-zinc-500">Loading …</td>
          </tr>
          <tr v-else-if="!rows.length">
            <td colspan="6" class="px-4 py-6 text-center text-zinc-500">No spools yet.</td>
          </tr>
          <SpoolRow
            v-for="spool in rows"
            :key="spool.id"
            :spool="spool"
            :live="change.available"
            @load="loadSpool(spool)"
            @unload="unloadSpool(spool)"
            @weigh="weighing = spool"
            @edit="editing = spool"
            @archive="run(() => filament.update(spool, { archived: true }), `${spool.name} archived`)"
            @restore="run(() => filament.update(spool, { archived: false }), `${spool.name} restored`)"
            @remove="remove(spool)"
          />
        </tbody>
      </table>
    </div>

    <SpoolFormModal v-if="creating" @close="creating = false" />
    <SpoolFormModal v-if="editing" :spool="editing" @close="editing = null" />
    <SpoolWeighModal v-if="weighing" :spool="weighing" @close="weighing = null" />
    <PaletteModal v-if="sharing" @close="sharing = false" />
  </div>
</template>
