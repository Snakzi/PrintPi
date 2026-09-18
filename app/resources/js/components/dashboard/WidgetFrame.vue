<script setup>
import { computed, provide, useId } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import Icon from '../Icon.vue';
import IconButton from '../IconButton.vue';
import WidgetEmpty from './WidgetEmpty.vue';

const props = defineProps({
  item: { type: Object, required: true },
  meta: { type: Object, required: true },
  icon: { type: String, default: 'grid' },
  editing: { type: Boolean, default: false },
});
const emit = defineEmits(['remove']);

const printer = usePrinterStore();
const blocked = computed(() => props.meta.needs_connection && !printer.connected);

// Widgets teleport their secondary controls into the header through WidgetActions.
const actionsId = `widget-actions-${useId()}`;
provide('widgetActions', `#${actionsId}`);
</script>

<template>
  <section
    class="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border bg-zinc-900 transition-colors"
    :class="editing ? 'border-zinc-600' : 'border-zinc-800'"
  >
    <header
      class="flex h-10 shrink-0 items-center gap-2 border-b border-zinc-800 pr-2 pl-3"
      :class="editing ? 'widget-drag-handle cursor-move bg-zinc-800/50 select-none' : ''"
    >
      <Icon :name="editing ? 'grip' : icon" fallback="grid" class="size-4 shrink-0 text-zinc-500" />
      <h2 class="truncate text-[13px] font-medium text-zinc-300">{{ meta.title }}</h2>
      <div v-show="!editing" :id="actionsId" class="ml-auto flex min-w-0 items-center gap-1" />
      <IconButton v-if="editing" icon="x" :title="`Remove ${meta.title}`" class="ml-auto hover:text-red-400" @click.stop="emit('remove')" />
    </header>

    <WidgetEmpty v-if="blocked" :icon="icon" message="Printer not connected" />
    <div v-else class="@container min-h-0 flex-1 overflow-auto p-3" :class="editing ? 'pointer-events-none opacity-60' : ''">
      <slot />
    </div>
  </section>
</template>
