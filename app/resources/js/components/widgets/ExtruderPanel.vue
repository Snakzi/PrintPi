<script setup>
import { computed, ref } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { useToastStore } from '../../stores/toasts';
import { formatTemp } from '../../format';
import ActionButton from '../ActionButton.vue';
import Icon from '../Icon.vue';
import SegmentedControl from '../SegmentedControl.vue';
import WidgetActions from '../dashboard/WidgetActions.vue';

const printer = usePrinterStore();
const toasts = useToastStore();

const length = ref(5);
const lengths = [1, 5, 10, 50].map((value) => ({ value, label: String(value), title: `${value} mm` }));
const FEED_E = 300;
const MIN_EXTRUDE_TEMP = 170;

const hotend = computed(() => printer.hotend?.actual ?? null);
const hotendHot = computed(() => (hotend.value ?? 0) >= MIN_EXTRUDE_TEMP);

async function extrude(direction) {
  const amount = (direction * length.value).toFixed(1);
  try {
    await printer.sendAll(['M83', `G1 E${amount} F${FEED_E}`, 'M82']);
  } catch (error) {
    toasts.error(error.message);
    throw error;
  }
}
</script>

<template>
  <div class="flex h-full flex-col gap-3">
    <WidgetActions>
      <SegmentedControl v-model="length" :options="lengths" />
      <span class="pr-1 text-xs text-zinc-500">mm</span>
    </WidgetActions>

    <div class="grid grid-cols-2 gap-2">
      <ActionButton icon="arrow-down" block :disabled="!hotendHot" :action="() => extrude(1)">Extrude</ActionButton>
      <ActionButton icon="arrow-up" block :disabled="!hotendHot" :action="() => extrude(-1)">Retract</ActionButton>
    </div>

    <p class="mt-auto flex items-center gap-1.5 text-xs tabular-nums" :class="hotendHot ? 'text-zinc-500' : 'text-amber-300'">
      <Icon name="nozzle" class="size-4" />
      <span>Hotend {{ formatTemp(hotend, 0) }} °C</span>
      <span v-if="!hotendHot">· min {{ MIN_EXTRUDE_TEMP }} °C</span>
    </p>
  </div>
</template>
