<script setup>
import JobStateBadge from '../job/JobStateBadge.vue';

defineProps({ job: { type: Object, required: true } });
</script>

<template>
  <div class="flex items-center gap-3 text-xs">
    <span class="min-w-0 truncate font-medium text-zinc-200" :title="job.name">{{ job.name }}</span>
    <span class="ml-auto flex shrink-0 items-center gap-3 text-zinc-400 tabular-nums">
      <span v-if="job.layer">Layer {{ job.layer }}<template v-if="job.total_layers"> / {{ job.total_layers }}</template></span>
      <span class="font-medium text-zinc-200">{{ Math.round(job.progress * 100) }} %</span>
    </span>
    <JobStateBadge :state="job.state" />
  </div>
</template>
