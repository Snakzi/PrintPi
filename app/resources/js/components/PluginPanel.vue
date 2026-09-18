<script setup>
import { computed } from 'vue';
import { usePluginStore } from '../stores/plugins';
import { usePrinterStore } from '../stores/printer';
import { useToastStore } from '../stores/toasts';
import { controlComponent } from '../pluginControls';
import Icon from './Icon.vue';
import PluginStatusBadge from './PluginStatusBadge.vue';

/* Embedded inside a dashboard widget the panel drops its own card and shrinks the header;
   headless leaves the name and badge to the surrounding page. controls narrows the manifest
   controls to a subset, the page uses it to give panel-sized controls a section of their own,
   and compact renders those in their dashboard form. */
const props = defineProps({
  plugin: { type: Object, required: true },
  controls: { type: Array, default: null },
  embedded: { type: Boolean, default: false },
  headless: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
});
const plugins = usePluginStore();
const printer = usePrinterStore();
const toasts = useToastStore();

const controls = computed(() => props.controls ?? props.plugin.controls);
const status = computed(() => props.plugin.daemon?.status ?? {});
const disabled = computed(() => !printer.daemonAlive || props.plugin.daemon?.state !== 'running');

async function act(action, value, key = null) {
  try {
    await plugins.act(props.plugin.id, action, value, key);
  } catch (error) {
    toasts.error(error.message);
  }
}

const change = (control, value) => act(control.action, value, control.key);
</script>

<template>
  <section :class="embedded ? '' : 'rounded-lg border border-zinc-800 bg-zinc-900 p-6'">
    <template v-if="!headless">
      <div class="flex items-center justify-between gap-3">
        <h2 class="flex min-w-0 items-center gap-2 font-semibold" :class="embedded ? 'text-sm' : 'text-lg'">
          <Icon :name="plugin.icon || 'puzzle'" fallback="puzzle" class="text-emerald-400" :class="embedded ? 'size-4' : 'size-5'" />
          <span class="truncate">{{ plugin.name }}</span>
        </h2>
        <PluginStatusBadge :plugin="plugin" />
      </div>
      <p v-if="plugin.daemon?.error" class="mt-2 text-sm text-red-400">{{ plugin.daemon.error }}</p>
      <p v-else-if="status.hint" class="mt-2 text-sm text-amber-300">{{ status.hint }}</p>
    </template>
    <div class="flex flex-col" :class="[headless ? '' : embedded ? 'mt-2.5' : 'mt-4', embedded ? 'gap-2.5' : 'gap-3']">
      <component
        :is="controlComponent(control, compact)"
        v-for="control in controls"
        :key="control.key"
        :control="control"
        :value="status[control.key] ?? null"
        :disabled="disabled"
        @change="change(control, $event)"
        @act="act($event.action, $event.value)"
      />
    </div>
  </section>
</template>
