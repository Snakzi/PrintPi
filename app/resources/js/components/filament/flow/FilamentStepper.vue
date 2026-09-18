<script setup>
import { computed } from 'vue';
import { STEP_LABELS, stepStatus, stepperSteps } from '../../../filament/walkthrough';
import Icon from '../../Icon.vue';

/* The steps of the walkthrough as dots on a line: done ones ticked, the current one lit, the
   rest dim. Vertical on the panel, a row in the modal. */
const props = defineProps({
  state: { type: Object, required: true },
  vertical: { type: Boolean, default: false },
});

const steps = computed(() =>
  stepperSteps(props.state).map((step, index) => ({
    id: step,
    label: STEP_LABELS[step] ?? step,
    status: stepStatus(props.state, index),
    here: index === (props.state.step_index ?? -1),
  })),
);

const DOT = {
  done: 'bg-emerald-500 text-zinc-950',
  current: 'bg-emerald-500/20 text-emerald-300 ring-2 ring-emerald-400',
  upcoming: 'bg-zinc-800 text-zinc-600',
};
const LABEL = { done: 'text-zinc-400', current: 'text-zinc-50 font-semibold', upcoming: 'text-zinc-600' };
</script>

<template>
  <ol class="flex" :class="vertical ? 'flex-col gap-0' : 'flex-row items-start'" aria-label="Steps">
    <li v-for="(step, index) in steps" :key="index" class="relative flex min-w-0" :class="vertical ? 'flex-row items-stretch gap-3' : 'flex-1 flex-col items-center gap-2'">
      <!-- the line to the next dot -->
      <span
        v-if="index < steps.length - 1"
        class="absolute bg-zinc-800"
        :class="[
          vertical ? 'top-7 bottom-0 left-[13px] w-0.5' : 'top-[13px] right-0 left-1/2 h-0.5',
          step.status === 'done' ? 'bg-emerald-500/60' : '',
        ]"
      />
      <span class="relative z-10 flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold tabular-nums transition-colors" :class="DOT[step.status]">
        <Icon v-if="step.status === 'done'" name="check" class="size-4" />
        <Icon v-else-if="step.id === 'error' || step.id === 'cancelled'" name="x" class="size-4" />
        <span v-else>{{ index + 1 }}</span>
      </span>
      <!-- On a phone only the current step keeps its word; the numbers say the rest. -->
      <span
        class="truncate leading-7"
        :class="[LABEL[step.status], vertical ? 'pb-4 text-sm' : 'px-1 text-center text-xs sm:text-sm', !vertical && !step.here ? 'max-sm:sr-only' : '']"
      >
        {{ step.label }}
      </span>
    </li>
  </ol>
</template>
