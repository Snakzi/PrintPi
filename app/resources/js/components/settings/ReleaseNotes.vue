<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import AppButton from '../AppButton.vue';

const props = defineProps({ notes: { type: String, required: true } });
const content = ref(null);
const expanded = ref(false);
const overflowing = ref(false);
let observer = null;

function measure() {
  if (!content.value) return;
  const lineHeight = parseFloat(getComputedStyle(content.value).lineHeight);
  overflowing.value = content.value.scrollHeight > lineHeight * 6 + 1;
}

watch(() => props.notes, async () => {
  expanded.value = false;
  await nextTick();
  measure();
});
onMounted(() => {
  observer = new ResizeObserver(measure);
  observer.observe(content.value);
  measure();
});
onUnmounted(() => observer?.disconnect());
</script>

<template>
  <div class="flex w-full min-w-0 flex-col items-start gap-2">
    <p ref="content" class="w-full text-sm leading-6 whitespace-pre-wrap wrap-anywhere text-zinc-300" :class="{ 'line-clamp-6': !expanded }">{{ notes }}</p>
    <AppButton v-if="overflowing" variant="ghost" size="sm" :aria-expanded="expanded" @click="expanded = !expanded">
      {{ expanded ? 'Show less' : 'Show more' }}
    </AppButton>
  </div>
</template>
