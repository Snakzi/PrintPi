<script setup>
import { ref } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { useToastStore } from '../../stores/toasts';
import SliderField from '../SliderField.vue';

const printer = usePrinterStore();
const toasts = useToastStore();

const fan = ref(0);
const speed = ref(100);
const flow = ref(100);

async function send(command) {
  try {
    await printer.send(command);
  } catch (error) {
    toasts.error(error.message);
  }
}

const setFan = (value) => send(`M106 S${Math.round((value / 100) * 255)}`);
const setSpeed = (value) => send(`M220 S${Math.round(value)}`);
const setFlow = (value) => send(`M221 S${Math.round(value)}`);
</script>

<template>
  <div class="flex h-full flex-col justify-between gap-3">
    <SliderField v-model="fan" label="Part fan" :min="0" :max="100" :step="5" @change="setFan" />
    <SliderField v-model="speed" label="Speed" :min="25" :max="200" :step="5" @change="setSpeed" />
    <SliderField v-model="flow" label="Flow" :min="50" :max="150" :step="1" @change="setFlow" />
  </div>
</template>
