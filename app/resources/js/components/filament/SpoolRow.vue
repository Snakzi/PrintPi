<script setup>
import { spoolDetail } from '../../filament/spools';
import { formatDate, formatFilament } from '../../format';
import AppButton from '../AppButton.vue';
import IconButton from '../IconButton.vue';
import SpoolRemaining from './SpoolRemaining.vue';
import SpoolSwatch from './SpoolSwatch.vue';

/* One spool of the inventory; the load button doubles as the loaded badge and unloads when
   pressed again. `live` says the buttons drive the printer rather than only the books. An
   archived spool is dimmed and can only be restored or deleted. */
defineProps({
  spool: { type: Object, required: true },
  live: { type: Boolean, default: false },
});
const emit = defineEmits(['load', 'unload', 'weigh', 'edit', 'archive', 'restore', 'remove']);
</script>

<template>
  <tr class="border-t border-zinc-800 hover:bg-zinc-800/50" :class="{ 'opacity-50': spool.archived_at }">
    <td class="max-w-xs px-4 py-3">
      <div class="flex items-center gap-3">
        <SpoolSwatch :color="spool.color" :finish="spool.finish" size="lg" />
        <div class="min-w-0">
          <div class="truncate font-medium" :title="spool.name">{{ spool.name }}</div>
          <div class="truncate text-xs text-zinc-500">{{ spoolDetail(spool) || '–' }}</div>
        </div>
      </div>
    </td>
    <td class="hidden px-4 py-3 whitespace-nowrap text-zinc-400 tabular-nums lg:table-cell">{{ spool.diameter }} mm</td>
    <td class="w-44 min-w-36 px-4 py-3">
      <SpoolRemaining :spool="spool" />
    </td>
    <td class="hidden px-4 py-3 whitespace-nowrap text-zinc-400 tabular-nums xl:table-cell">{{ formatFilament(spool.weight, null) }}</td>
    <td class="hidden px-4 py-3 whitespace-nowrap text-zinc-400 xl:table-cell">{{ formatDate(spool.created_at) }}</td>
    <td class="px-4 py-3">
      <div class="flex items-center justify-end gap-1">
        <AppButton v-if="spool.loaded" size="sm" variant="success" icon="check" :title="live ? 'Unload from the printer' : 'Mark as unloaded'" class="mr-1" @click="emit('unload')">Loaded</AppButton>
        <AppButton v-else-if="!spool.archived_at" size="sm" :icon="live ? 'arrow-down' : null" :title="live ? 'Load into the printer' : 'Mark as loaded'" class="mr-1" @click="emit('load')">Load</AppButton>
        <IconButton icon="scale" title="Weigh" :disabled="Boolean(spool.archived_at)" @click="emit('weigh')" />
        <IconButton icon="pencil" title="Edit" :disabled="Boolean(spool.archived_at)" @click="emit('edit')" />
        <IconButton v-if="spool.archived_at" icon="refresh" title="Restore" @click="emit('restore')" />
        <IconButton v-else icon="archive" title="Archive" @click="emit('archive')" />
        <IconButton icon="trash" title="Delete" class="hover:text-red-400" @click="emit('remove')" />
      </div>
    </td>
  </tr>
</template>
