<script setup>
import { ref } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { useToastStore } from '../../stores/toasts';
import ActionButton from '../ActionButton.vue';
import SegmentedControl from '../SegmentedControl.vue';
import WidgetActions from '../dashboard/WidgetActions.vue';
import AxisReadout from '../motion/AxisReadout.vue';
import JogPad from '../motion/JogPad.vue';

const printer = usePrinterStore();
const toasts = useToastStore();

const step = ref(10);
const steps = [0.1, 1, 10, 50].map((value) => ({ value, label: String(value), title: `${value} mm` }));
const FEED_XY = 3000;
const FEED_Z = 600;

async function run(commands) {
  try {
    await printer.sendAll(commands);
  } catch (error) {
    toasts.error(error.message);
    throw error;
  }
}

function jog(axis, direction) {
  const distance = (direction * step.value).toFixed(2);
  return run(['G91', `G1 ${axis}${distance} F${axis === 'Z' ? FEED_Z : FEED_XY}`, 'G90']).catch(() => {});
}

function home(axes = '') {
  return run([`G28 ${axes}`.trim()]);
}
</script>

<template>
  <div class="flex h-full flex-col gap-3 @md:flex-row @md:items-start @md:gap-4">
    <WidgetActions>
      <SegmentedControl v-model="step" :options="steps" />
      <span class="pr-1 text-xs text-zinc-500">mm</span>
    </WidgetActions>

    <JogPad @jog="jog" @home="(axes) => home(axes).catch(() => {})" />

    <div class="flex min-w-0 flex-1 flex-col gap-2">
      <AxisReadout :position="printer.printer.position" />
      <div class="grid grid-cols-1 gap-2 @xs:grid-cols-3">
        <ActionButton size="sm" icon="home" block :action="() => home()">Home all</ActionButton>
        <ActionButton size="sm" icon="refresh" block title="M114" :action="() => run(['M114'])">Position</ActionButton>
        <ActionButton size="sm" icon="power" block title="M84" :action="() => run(['M84'])">Motors off</ActionButton>
      </div>
    </div>
  </div>
</template>
