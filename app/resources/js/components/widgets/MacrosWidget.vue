<script setup>
import { computed, onMounted, ref } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { useSettingsStore } from '../../stores/settings';
import { useToastStore } from '../../stores/toasts';
import ActionButton from '../ActionButton.vue';
import AppButton from '../AppButton.vue';
import IconButton from '../IconButton.vue';
import WidgetActions from '../dashboard/WidgetActions.vue';
import WidgetEmpty from '../dashboard/WidgetEmpty.vue';
import MacroEditor from './MacroEditor.vue';

const printer = usePrinterStore();
const settings = useSettingsStore();
const toasts = useToastStore();

const editing = ref(false);
const macros = computed(() => settings.values.macros ?? []);

onMounted(async () => {
  if (settings.loaded) return;
  try {
    await settings.load();
  } catch (error) {
    toasts.error(error.message);
  }
});

async function run(macro) {
  const commands = macro.gcode
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  try {
    await printer.sendAll(commands);
  } catch (error) {
    toasts.error(error.message);
    throw error;
  }
}

async function save(next) {
  try {
    await settings.save({ macros: next });
    editing.value = false;
    toasts.success('Quick commands saved');
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <div class="flex h-full flex-col">
    <WidgetActions>
      <IconButton icon="pencil" title="Edit" :active="editing" @click="editing = !editing" />
    </WidgetActions>

    <MacroEditor v-if="editing" :macros="macros" :saving="settings.saving" @save="save" @cancel="editing = false" />

    <WidgetEmpty v-else-if="!macros.length" icon="bolt" message="No quick commands">
      <AppButton size="sm" variant="ghost" icon="plus" @click="editing = true">Add</AppButton>
    </WidgetEmpty>

    <div v-else class="grid grid-cols-2 content-start gap-2 @sm:grid-cols-3">
      <ActionButton v-for="(macro, index) in macros" :key="index" size="sm" block :title="macro.gcode" :action="() => run(macro)">
        <span class="truncate">{{ macro.label }}</span>
      </ActionButton>
    </div>
  </div>
</template>
