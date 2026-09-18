<script setup>
import JobStateBadge from './JobStateBadge.vue';

/* Name and state of a job. */
defineProps({
  job: { type: Object, required: true },
  preparing: { type: Boolean, default: false },
});
</script>

<template>
  <div class="flex min-w-0 items-center justify-between gap-3">
    <div class="truncate text-sm font-medium text-zinc-100" :title="job.name">{{ job.name }}</div>
    <JobStateBadge :state="job.state" :preparing="preparing" :activity="job.activity" class="shrink-0" />
  </div>
</template>
