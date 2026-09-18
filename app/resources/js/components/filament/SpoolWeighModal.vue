<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useFilamentStore } from '../../stores/filament';
import { useToastStore } from '../../stores/toasts';
import { millimetresFor } from '../../filament/spools';
import { formatFilament } from '../../format';
import AppButton from '../AppButton.vue';
import Modal from '../Modal.vue';
import SettingsField from '../settings/SettingsField.vue';
import SpoolPreview from './SpoolPreview.vue';
import { inputClass } from '../settings/styles';

/* Corrects what is left of a spool from a scale: the reading minus the empty spool, shown
   live in the preview before it is saved. */
const props = defineProps({ spool: { type: Object, required: true } });
const emit = defineEmits(['close']);

const filament = useFilamentStore();
const toasts = useToastStore();

const form = reactive({
  reading: '',
  spool_weight: props.spool.spool_weight ?? '',
});
const saving = ref(false);
const reading = ref(null);

// The modal is teleported, so the autofocus attribute would not take.
onMounted(() => reading.value?.focus());

const remaining = computed(() => {
  if (form.reading === '' || form.spool_weight === '') return null;
  return Math.max(0, Number(form.reading) - Number(form.spool_weight));
});
const draft = computed(() => {
  const grams = remaining.value ?? props.spool.remaining;
  return { ...props.spool, remaining: grams, remaining_mm: millimetresFor(props.spool, grams) };
});

async function save() {
  if (remaining.value === null) return;
  saving.value = true;
  try {
    await filament.update(props.spool, { remaining: remaining.value, spool_weight: Number(form.spool_weight) });
    toasts.success(`${props.spool.name}: ${formatFilament(remaining.value, null)} left`);
    emit('close');
  } catch (error) {
    toasts.error(error.message);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Modal size="md" @close="emit('close')">
    <template #title>
      <h2 class="font-medium">Weigh {{ spool.name }}</h2>
    </template>
    <form class="flex flex-col" @submit.prevent="save">
      <SpoolPreview :spool="draft" :color="spool.color" />
      <div class="grid gap-4 p-4 sm:grid-cols-2">
        <SettingsField label="Scale reading (g)">
          <input ref="reading" v-model="form.reading" type="number" min="0" max="25000" step="1" inputmode="numeric" required :class="inputClass">
        </SettingsField>
        <SettingsField label="Empty spool (g)">
          <input v-model="form.spool_weight" type="number" min="0" max="5000" step="1" inputmode="numeric" required :class="inputClass">
        </SettingsField>
      </div>
      <div class="flex justify-end gap-2 border-t border-zinc-800 px-4 py-3">
        <AppButton variant="ghost" @click="emit('close')">Cancel</AppButton>
        <AppButton type="submit" variant="primary" icon="check" :disabled="saving || remaining === null">Save</AppButton>
      </div>
    </form>
  </Modal>
</template>
