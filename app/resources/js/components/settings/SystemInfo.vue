<script setup>
import { computed } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { useUpdatesStore } from '../../stores/updates';
import { formatBytes } from '../../format';
import { formatUptime, throttleIssues } from '../../system/host';
import SettingsCard from './SettingsCard.vue';
import ThrottleStatus from './ThrottleStatus.vue';

/* The host PrintPi runs on, from the stats the daemon publishes with its heartbeat. */
const printer = usePrinterStore();
const updates = useUpdatesStore();

const system = computed(() => printer.system);
const issues = computed(() => throttleIssues(system.value?.throttled));

const rows = computed(() => {
  const s = system.value;
  if (!s) return [];
  return [
    { label: 'Model', value: s.model ?? s.platform },
    { label: 'System', value: [s.os, s.kernel, s.arch].filter(Boolean).join(' · ') || null },
    { label: 'Hostname', value: [s.hostname, s.ip].filter(Boolean).join(' · ') || null },
    { label: 'Uptime', value: formatUptime(s.uptime_seconds) },
    { label: 'CPU', value: cpu(s) },
    { label: 'Memory', value: s.memory ? `${s.memory.used_percent} % of ${formatBytes(s.memory.total)}` : null },
    { label: 'Storage', value: s.disk ? `${formatBytes(s.disk.free)} free of ${formatBytes(s.disk.total)}` : null },
  ];
});

function cpu(s) {
  const parts = [];
  if (s.cpu_temperature != null) parts.push(`${s.cpu_temperature.toFixed(1)} °C`);
  if (s.load) parts.push(`load ${s.load[0].toFixed(2)} on ${s.cpu_count ?? '?'} cores`);
  return parts.join(' · ') || null;
}
</script>

<template>
  <SettingsCard title="Host" :form="false">
    <dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-6 gap-y-1 text-sm text-zinc-300">
      <dt class="text-zinc-500">PrintPi</dt>
      <dd>{{ updates.installed ?? '–' }} <span class="text-zinc-500">· daemon {{ printer.daemonAlive ? 'running' : 'unreachable' }}</span></dd>
      <template v-for="row in rows" :key="row.label">
        <dt class="text-zinc-500">{{ row.label }}</dt>
        <dd class="truncate" :title="row.value ?? ''">{{ row.value ?? '–' }}</dd>
      </template>
      <template v-if="system?.throttled">
        <dt class="text-zinc-500">Power</dt>
        <dd><ThrottleStatus :issues="issues" /></dd>
      </template>
    </dl>
  </SettingsCard>
</template>
