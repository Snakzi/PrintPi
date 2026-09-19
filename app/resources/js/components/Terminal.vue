<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import { useVisible } from '../composables/useVisible';
import { usePrinterStore } from '../stores/printer';
import Icon from './Icon.vue';
import ToggleButton from './ToggleButton.vue';
import WidgetActions from './dashboard/WidgetActions.vue';
import TerminalLine from './terminal/TerminalLine.vue';

/** embedded: rendered inside a dashboard widget frame that already provides card and title. */
defineProps({ embedded: { type: Boolean, default: false } });

const printer = usePrinterStore();
const input = ref('');
const hideTemperatures = ref(true);
const history = ref([]);
const historyIndex = ref(-1);
const scroller = ref(null);
const visible = useVisible(scroller);
const error = ref(null);

watch(visible, (active, previous, onCleanup) => {
  if (!active) return;
  printer.serialConsumers += 1;
  onCleanup(() => { printer.serialConsumers -= 1; });
}, { flush: 'sync' });

const TEMPERATURE_LINE = /^(ok\s+)?\s*T\d*:\s*-?\d/;

const lines = computed(() =>
  printer.serial.filter((entry) => !(hideTemperatures.value && TEMPERATURE_LINE.test(entry.line))),
);

async function submit() {
  const command = input.value.trim();
  if (!command) return;
  error.value = null;
  try {
    await printer.send(command);
    history.value.unshift(command);
    historyIndex.value = -1;
    input.value = '';
  } catch (e) {
    error.value = e.message;
  }
}

function recall(offset) {
  const next = historyIndex.value + offset;
  if (next < -1 || next >= history.value.length) return;
  historyIndex.value = next;
  input.value = next === -1 ? '' : history.value[next];
}

watch(lines, async () => {
  const element = scroller.value;
  if (!element) return;
  const atBottom = element.scrollHeight - element.scrollTop - element.clientHeight < 40;
  if (atBottom) {
    await nextTick();
    element.scrollTop = element.scrollHeight;
  }
});
</script>

<template>
  <section class="flex flex-col" :class="embedded ? 'h-full min-h-0' : 'min-h-96 rounded-lg border border-zinc-800 bg-zinc-900 p-4'">
    <div :class="embedded ? 'contents' : 'mb-3 flex items-center gap-4'">
      <h2 v-if="!embedded" class="text-sm font-semibold tracking-wide text-zinc-400 uppercase">Terminal</h2>
      <WidgetActions>
        <ToggleButton v-model="hideTemperatures">Hide temperatures</ToggleButton>
      </WidgetActions>
    </div>

    <div ref="scroller" class="min-h-32 flex-1 overflow-y-auto rounded-md bg-zinc-950 p-2 font-mono text-xs leading-5">
      <div v-if="!lines.length" class="text-zinc-600">Nothing received yet</div>
      <TerminalLine v-for="(entry, index) in lines" :key="index" :entry="entry" />
    </div>

    <form
      class="mt-2 flex items-center gap-2 rounded-md border border-zinc-700 bg-zinc-950 pr-1 pl-3 transition-colors focus-within:border-emerald-500"
      :class="printer.connected ? '' : 'opacity-50'"
      @submit.prevent="submit"
    >
      <span class="font-mono text-sm text-zinc-500 select-none">›</span>
      <input
        v-model="input"
        type="text"
        placeholder="G-code"
        autocomplete="off"
        spellcheck="false"
        class="h-9 min-w-0 flex-1 bg-transparent font-mono text-sm outline-none placeholder:text-zinc-600"
        :disabled="!printer.connected"
        @keydown.up.prevent="recall(1)"
        @keydown.down.prevent="recall(-1)"
      >
      <button
        type="submit"
        title="Send"
        aria-label="Send"
        class="flex size-7 items-center justify-center rounded-md text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="!printer.connected || !input.trim()"
      >
        <Icon name="send" class="size-4" />
      </button>
    </form>
    <p v-if="error" class="mt-2 text-xs text-red-400">{{ error }}</p>
  </section>
</template>
