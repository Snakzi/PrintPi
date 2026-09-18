<script setup>
import { computed, ref, watch } from 'vue';
import DeviceReadings from './DeviceReadings.vue';
import Icon from './Icon.vue';
import IconButton from './IconButton.vue';
import InlineEdit from './InlineEdit.vue';
import ToggleSwitch from './ToggleSwitch.vue';

/* One added plug: name, readings and its switch; compact drops model, address and editing
   for the dashboard, removable adds the remove button on the plugin page, where the name
   can also be changed in place and the plug can be marked as the one powering the printer. */
const props = defineProps({
  device: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  removable: { type: Boolean, default: false },
});
const emit = defineEmits(['power', 'rename', 'remove', 'printer']);

/* The plug answers within a second or two; the switch shows the requested state until the
   plugin's status agrees or the request evidently failed. The name works the same way. */
const requested = ref(null);
let timer = null;
watch(
  () => props.device.on,
  (on) => {
    if (requested.value !== null && on === requested.value) settle();
  },
);
function settle() {
  clearTimeout(timer);
  requested.value = null;
}
function toggle(on) {
  requested.value = on;
  clearTimeout(timer);
  timer = setTimeout(settle, 5000);
  emit('power', on);
}

const pendingName = ref(null);
let nameTimer = null;
watch(
  () => props.device.name,
  () => {
    clearTimeout(nameTimer);
    pendingName.value = null;
  },
);
function rename(name) {
  pendingName.value = name || props.device.plug_name || props.device.name;
  clearTimeout(nameTimer);
  nameTimer = setTimeout(() => (pendingName.value = null), 5000);
  emit('rename', name);
}

const on = computed(() => requested.value ?? Boolean(props.device.on));
const name = computed(() => pendingName.value ?? props.device.name);
const detail = computed(() => {
  const plugName = props.device.plug_name && props.device.plug_name !== name.value ? props.device.plug_name : null;
  return [plugName, props.device.model, props.device.host].filter(Boolean).join(' · ');
});
</script>

<template>
  <div class="flex items-center gap-3 text-sm" :class="compact ? '' : 'px-3 py-2'">
    <div class="flex min-w-0 flex-1 flex-col">
      <InlineEdit
        v-if="removable"
        :model-value="name"
        :label="`Rename ${name}`"
        :placeholder="device.plug_name || device.model"
        :disabled="disabled"
        class="text-zinc-200"
        @update:model-value="rename"
      />
      <span v-else class="flex items-center gap-1.5 truncate text-zinc-200">
        <Icon v-if="device.printer" name="printer" class="size-3.5 shrink-0 text-emerald-400" title="Powers the printer" />
        {{ name }}
      </span>
      <span v-if="!compact && detail" class="truncate text-xs text-zinc-500">{{ detail }}</span>
      <DeviceReadings :device="device" />
    </div>
    <IconButton
      v-if="removable"
      icon="printer"
      :title="device.printer ? 'Powers the printer' : 'Mark as the printer plug'"
      :active="Boolean(device.printer)"
      :disabled="disabled"
      @click="emit('printer', !device.printer)"
    />
    <ToggleSwitch :model-value="on" :disabled="disabled || device.online === false" :label="name" @update:model-value="toggle" />
    <IconButton v-if="removable" icon="trash" :title="`Remove ${name}`" :disabled="disabled" class="hover:text-red-400" @click="emit('remove')" />
  </div>
</template>
