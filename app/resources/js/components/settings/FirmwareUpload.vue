<script setup>
import { ref } from 'vue';
import { formatBytes } from '../../format';
import AppButton from '../AppButton.vue';
import Icon from '../Icon.vue';

/* A .hex or .bin for avrdude. */
defineProps({
  disabled: { type: Boolean, default: false },
  available: { type: Boolean, default: true },
});
const emit = defineEmits(['flash']);

const input = ref(null);
const file = ref(null);

function onPick(event) {
  file.value = event.target.files?.[0] ?? null;
  event.target.value = '';
}
</script>

<template>
  <div class="flex flex-col gap-3 rounded-md border border-zinc-800 p-4">
    <h3 class="font-semibold">Firmware file</h3>
    <p v-if="!available" class="text-sm text-amber-400" role="status">avrdude is not installed on this host</p>
    <div class="flex flex-wrap items-center gap-3">
      <AppButton variant="secondary" icon="upload" :disabled="disabled" @click="input.click()">Choose .hex or .bin</AppButton>
      <span v-if="file" class="flex items-center gap-2 text-sm text-zinc-300">
        <Icon name="document" class="size-4 text-zinc-500" />
        {{ file.name }} · {{ formatBytes(file.size) }}
      </span>
      <input ref="input" type="file" accept=".hex,.bin" class="hidden" @change="onPick">
      <AppButton v-if="file" variant="primary" icon="bolt" :disabled="disabled || !available" @click="emit('flash', file)">Flash {{ file.name }}</AppButton>
    </div>
  </div>
</template>
