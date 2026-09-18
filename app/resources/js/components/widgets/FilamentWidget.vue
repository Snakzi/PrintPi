<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { useFilamentStore } from '../../stores/filament';
import { useFilamentChangeStore } from '../../stores/filamentChange';
import { useToastStore } from '../../stores/toasts';
import { remainingFraction, spoolDetail } from '../../filament/spools';
import AppButton from '../AppButton.vue';
import IconButton from '../IconButton.vue';
import SpoolLoadedMark from '../filament/SpoolLoadedMark.vue';
import SpoolRemaining from '../filament/SpoolRemaining.vue';
import SpoolGraphic from '../filament/SpoolGraphic.vue';
import SpoolSelect from '../filament/SpoolSelect.vue';
import SpoolWeighModal from '../filament/SpoolWeighModal.vue';
import WidgetActions from '../dashboard/WidgetActions.vue';
import WidgetEmpty from '../dashboard/WidgetEmpty.vue';

/* A look at one spool and what is left of it. The select only picks which spool to show and
   never loads one; it follows the loaded spool whenever that changes, so the widget opens on
   the spool in the printer. With a connected, idle printer the arrow runs the filament
   walkthrough for the shown spool: in when it is not loaded, out when it is. */
const filament = useFilamentStore();
const change = useFilamentChangeStore();
const toasts = useToastStore();
const weighing = ref(false);
const selected = ref(null);

onMounted(async () => {
  try {
    await filament.ensure();
  } catch (error) {
    toasts.error(error.message);
  }
});

const current = computed(() => filament.current);
const shown = computed(() => filament.byId(selected.value) ?? current.value);

watch(
  () => current.value?.id ?? null,
  (id) => {
    selected.value = id;
  },
  { immediate: true },
);

async function swap() {
  try {
    if (shown.value.loaded) await change.unload();
    else await change.load({ spoolId: shown.value.id, unloadFirst: Boolean(current.value) });
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <div class="flex h-full flex-col">
    <WidgetActions>
      <IconButton icon="arrow-up-right" title="All spools" :to="{ name: 'filament' }" />
    </WidgetActions>

    <WidgetEmpty v-if="filament.loading && !filament.items.length" icon="spool" message="Loading…" />
    <WidgetEmpty v-else-if="!filament.active.length" icon="spool" message="No spools">
      <RouterLink v-slot="{ navigate }" :to="{ name: 'filament' }" custom>
        <AppButton size="sm" variant="ghost" icon="plus" @click="navigate">Add spool</AppButton>
      </RouterLink>
    </WidgetEmpty>

    <div v-else class="flex flex-1 flex-col gap-3">
      <SpoolSelect v-model="selected" none="No spool loaded" :allow-none="!current" mark-loaded class="w-full" />

      <template v-if="shown">
        <div class="flex items-center gap-3">
          <SpoolGraphic :color="shown.color" :finish="shown.finish" :fraction="remainingFraction(shown)" :size="44" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="truncate text-sm font-medium text-zinc-100" :title="shown.name">{{ shown.name }}</span>
              <SpoolLoadedMark v-if="shown.loaded" />
            </div>
            <div class="truncate text-xs text-zinc-500">{{ spoolDetail(shown) || '–' }}</div>
          </div>
          <IconButton v-if="change.available" :icon="shown.loaded ? 'arrow-up' : 'arrow-down'" :title="shown.loaded ? 'Unload' : 'Load'" @click="swap" />
          <IconButton icon="scale" title="Weigh" @click="weighing = true" />
        </div>
        <SpoolRemaining :spool="shown" />
      </template>
      <WidgetEmpty v-else icon="spool" message="No spool loaded" />
    </div>

    <SpoolWeighModal v-if="weighing && shown" :spool="shown" @close="weighing = false" />
  </div>
</template>
