<script setup>
import { reactive, ref } from 'vue';
import { usePluginStore } from '../stores/plugins';
import { useToastStore } from '../stores/toasts';
import SchemaField from './SchemaField.vue';

const props = defineProps({ plugin: { type: Object, required: true } });
const plugins = usePluginStore();
const toasts = useToastStore();

const values = reactive({ ...props.plugin.settings });
const errors = ref({});
const saving = ref(false);

async function save() {
  saving.value = true;
  errors.value = {};
  try {
    await plugins.saveSettings(props.plugin.id, { ...values });
    toasts.success(`${props.plugin.name} settings saved`);
  } catch (error) {
    errors.value = error.errors ?? {};
    toasts.error(error.message);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <form class="flex flex-col gap-4" @submit.prevent="save">
    <div class="grid gap-4 sm:grid-cols-2">
      <SchemaField
        v-for="field in plugin.schema"
        :key="field.key"
        v-model="values[field.key]"
        :field="field"
        :error="errors[field.key]?.[0]"
      />
    </div>
    <div>
      <button
        type="submit"
        class="rounded-md bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
        :disabled="saving"
      >
        Save
      </button>
    </div>
  </form>
</template>
