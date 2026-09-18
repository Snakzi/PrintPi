<script setup>
import { computed, onMounted, ref } from 'vue';

/* The extruder as a drawing that plays the current step: the filament slides in or out, the
   gears turn, the heater block glows while heating, a purge line grows out of the nozzle.
   `progress` (0..1) drives the geometry of the motion steps; the colour is the spool's, and
   `old` says the strand is still the filament coming out, drawn in a neutral tone. */
const props = defineProps({
  step: { type: String, required: true },
  action: { type: String, default: 'load' },
  old: { type: Boolean, default: false },
  progress: { type: Number, default: null },
  color: { type: String, default: null },
});

const STRAND_TOP = 0; // where the filament enters the picture
const GEARS = 96; // the pinch point of the gears
const TIP = 266; // the nozzle tip
const INSIDE = TIP - GEARS;
const NEW_COLOR = 'var(--color-zinc-300)';
const OLD_COLOR = 'var(--color-zinc-500)';

const fraction = computed(() => Math.min(1, Math.max(0, props.progress ?? 0)));
const color = computed(() => (props.old ? OLD_COLOR : props.color || NEW_COLOR));

// How much of the strand shows above the gears and inside the extruder, and how long the purge is.
const geometry = computed(() => {
  switch (props.step) {
    case 'heating':
      return props.old ? { above: 1, inside: 1, purge: 0 } : { above: 0, inside: 0, purge: 0 };
    case 'unloading':
      return { above: 1, inside: 1 - fraction.value, purge: 0 };
    case 'remove':
      return { above: 0.6, inside: 0, purge: 0 };
    case 'insert':
      return { above: 0.75, inside: 0, purge: 0 };
    case 'loading':
      return { above: 1, inside: fraction.value, purge: 0 };
    case 'purging':
      return { above: 1, inside: 1, purge: fraction.value };
    case 'check':
      return { above: 1, inside: 1, purge: 1 };
    case 'done':
      return props.action === 'unload' ? { above: 0, inside: 0, purge: 0 } : { above: 1, inside: 1, purge: 0.5 };
    default:
      return { above: 0, inside: 0, purge: 0 };
  }
});

const gearsTurn = computed(() => ['loading', 'purging', 'unloading'].includes(props.step));
const glow = computed(() => {
  if (props.step === 'heating') return 0.35 + 0.65 * fraction.value;
  if (['loading', 'purging', 'check', 'unloading', 'insert'].includes(props.step)) return 1;
  if (props.step === 'remove' && props.action === 'change') return 1;
  return 0;
});
const ended = computed(() => ['cancelled', 'error'].includes(props.step));
const purgePath = 'M110 266 C 110 290, 96 292, 96 304 S 118 316, 124 302';
const purge = ref(null);
const purgeLength = ref(100);
onMounted(() => {
  purgeLength.value = purge.value?.getTotalLength?.() ?? 100;
});
</script>

<template>
  <svg viewBox="0 0 220 330" class="extruder size-full" :class="{ 'opacity-40': ended }" aria-hidden="true">
    <defs>
      <radialGradient id="extruder-glow" cx="50%" cy="60%" r="60%">
        <stop offset="0%" stop-color="#fb923c" stop-opacity="0.9" />
        <stop offset="60%" stop-color="#ef4444" stop-opacity="0.35" />
        <stop offset="100%" stop-color="#ef4444" stop-opacity="0" />
      </radialGradient>
      <linearGradient id="extruder-heater" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#f97316" />
        <stop offset="100%" stop-color="#dc2626" />
      </linearGradient>
    </defs>

    <!-- heat -->
    <ellipse cx="110" cy="236" rx="70" ry="52" fill="url(#extruder-glow)" class="glow" :style="{ opacity: glow }" :class="{ pulse: step === 'heating' }" />

    <!-- the strand above the gears, nudged in or out while the user is asked to move it -->
    <g :class="{ 'nudge-in': step === 'insert', 'nudge-out': step === 'remove' }">
      <path
        :d="`M110 ${GEARS} L110 ${STRAND_TOP}`"
        fill="none"
        :stroke="color"
        stroke-width="9"
        stroke-linecap="round"
        :stroke-dasharray="GEARS - STRAND_TOP"
        :stroke-dashoffset="(GEARS - STRAND_TOP) * (1 - geometry.above)"
        :style="{ opacity: geometry.above ? 1 : 0 }"
        class="strand"
      />
      <!-- the loose end of a strand that is not held by the gears -->
      <circle v-if="geometry.above && geometry.above < 1" cx="110" :cy="GEARS - (GEARS - STRAND_TOP) * geometry.above" r="4.5" :fill="color" />
    </g>

    <!-- direction hints -->
    <g v-if="step === 'insert'" class="fill-emerald-400 nudge-in">
      <path d="M62 14 l0 22 M52 26 l10 12 l10 -12" fill="none" stroke="currentColor" class="text-emerald-400" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
    </g>
    <g v-if="step === 'remove'" class="nudge-out">
      <path d="M62 38 l0 -22 M52 26 l10 -12 l10 12" fill="none" stroke="currentColor" class="text-amber-400" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
    </g>

    <!-- extruder body -->
    <rect x="56" y="66" width="108" height="64" rx="12" class="fill-zinc-800" />
    <rect x="102" y="66" width="16" height="64" class="fill-zinc-900" />
    <!-- gears -->
    <g :class="{ spin: gearsTurn, reverse: step === 'unloading' }" style="transform-origin: 91px 96px">
      <circle cx="91" cy="96" r="15" class="fill-zinc-700" />
      <circle cx="91" cy="96" r="15" fill="none" class="stroke-zinc-600" stroke-width="5" stroke-dasharray="3 4.4" />
      <circle cx="91" cy="96" r="4" class="fill-zinc-900" />
    </g>
    <g :class="{ spin: gearsTurn, reverse: step !== 'unloading' }" style="transform-origin: 129px 96px">
      <circle cx="129" cy="96" r="15" class="fill-zinc-700" />
      <circle cx="129" cy="96" r="15" fill="none" class="stroke-zinc-600" stroke-width="5" stroke-dasharray="3 4.4" />
      <circle cx="129" cy="96" r="4" class="fill-zinc-900" />
    </g>

    <!-- heat sink -->
    <rect v-for="fin in 5" :key="fin" x="72" :y="140 + (fin - 1) * 13" width="76" height="7" rx="2" class="fill-zinc-700" />
    <rect x="102" y="136" width="16" height="70" class="fill-zinc-900" />
    <!-- heater block and nozzle -->
    <rect x="82" y="208" width="56" height="34" rx="4" class="fill-zinc-600" />
    <rect x="82" y="208" width="56" height="34" rx="4" fill="url(#extruder-heater)" :style="{ opacity: glow * 0.85 }" />
    <polygon points="92,242 128,242 116,266 104,266" class="fill-zinc-500" />
    <polygon points="92,242 128,242 116,266 104,266" fill="url(#extruder-heater)" :style="{ opacity: glow * 0.7 }" />

    <!-- the strand inside the extruder, from the gears to the tip -->
    <path
      :d="`M110 ${GEARS} L110 ${TIP}`"
      fill="none"
      :stroke="color"
      stroke-width="9"
      stroke-linecap="butt"
      :stroke-dasharray="INSIDE"
      :stroke-dashoffset="INSIDE * (1 - geometry.inside)"
      :style="{ opacity: geometry.inside ? 1 : 0 }"
      class="strand"
    />

    <!-- the purge line curling out of the nozzle -->
    <path
      ref="purge"
      :d="purgePath"
      fill="none"
      :stroke="color"
      stroke-width="7"
      stroke-linecap="round"
      :stroke-dasharray="purgeLength"
      :stroke-dashoffset="purgeLength * (1 - geometry.purge)"
      :style="{ opacity: geometry.purge ? 1 : 0 }"
      class="strand"
    />

    <!-- the verdict -->
    <g v-if="step === 'done'" class="pop" style="transform-origin: 176px 268px">
      <circle cx="176" cy="268" r="22" class="fill-emerald-500" />
      <path d="M165 268 l8 8 l14 -16" fill="none" stroke="white" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
    </g>
    <g v-else-if="ended" class="pop" style="transform-origin: 176px 268px">
      <circle cx="176" cy="268" r="22" :class="step === 'error' ? 'fill-red-500' : 'fill-zinc-600'" />
      <path d="M168 260 l16 16 M184 260 l-16 16" fill="none" stroke="white" stroke-width="4.5" stroke-linecap="round" />
    </g>
  </svg>
</template>

<style scoped>
.strand {
  transition:
    stroke-dashoffset 0.3s linear,
    opacity 0.3s;
}
circle {
  transition: cy 0.3s linear;
}
.glow {
  transition: opacity 0.6s;
}
.pulse {
  animation: extruder-pulse 1.3s ease-in-out infinite;
}
.spin {
  animation: extruder-spin 1.6s linear infinite;
}
.spin.reverse {
  animation-direction: reverse;
}
.nudge-in {
  animation: extruder-nudge-in 1.5s ease-in-out infinite;
}
.nudge-out {
  animation: extruder-nudge-out 1.5s ease-in-out infinite;
}
.pop {
  animation: extruder-pop 0.5s cubic-bezier(0.2, 1.4, 0.4, 1) both;
}
@keyframes extruder-pulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.12);
  }
}
@keyframes extruder-spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes extruder-nudge-in {
  0%,
  100% {
    transform: translateY(-10px);
  }
  50% {
    transform: translateY(4px);
  }
}
@keyframes extruder-nudge-out {
  0%,
  100% {
    transform: translateY(4px);
  }
  50% {
    transform: translateY(-10px);
  }
}
@keyframes extruder-pop {
  from {
    transform: scale(0.4);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}
.glow.pulse {
  transform-origin: 110px 236px;
}
</style>
