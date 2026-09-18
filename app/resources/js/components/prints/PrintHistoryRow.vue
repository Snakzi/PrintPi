<script setup>
import { computed } from 'vue';
import { formatDateTime, formatDuration, formatEnergy, formatFilament } from '../../format';
import FileThumbnail from '../FileThumbnail.vue';
import IconButton from '../IconButton.vue';
import JobStateBadge from '../job/JobStateBadge.vue';
import SpoolPicker from '../filament/SpoolPicker.vue';

/* One past print. `printable` means the file still exists and the printer could take it;
   `spool` carries the id of the spool the print is moved to. */
const props = defineProps({
  print: { type: Object, required: true },
  printable: { type: Boolean, default: false },
  postcard: { type: Boolean, default: true },
});
const emit = defineEmits(['open', 'print', 'spool', 'remove']);

/* Without the postcard the row only opens a timelapse when there is one. */
const opens = computed(() => props.postcard || Boolean(props.print.video_url || props.print.timelapse_url));

const picture = computed(() => ({ name: props.print.name, thumbnail_url: props.print.thumbnail_url ?? props.print.cover_url }));
</script>

<template>
  <tr class="border-t border-zinc-800 hover:bg-zinc-800/50">
    <td class="px-2 py-2">
      <button v-if="opens" type="button" class="block rounded ring-emerald-500 hover:ring-2" :title="postcard ? 'Postcard' : 'Timelapse'" @click="emit('open')">
        <FileThumbnail :file="picture" />
      </button>
      <FileThumbnail v-else :file="picture" />
    </td>
    <td class="max-w-xs px-4 py-2">
      <div class="truncate font-medium" :title="print.name">{{ print.name }}</div>
      <div v-if="print.printer" class="truncate text-xs text-zinc-500">{{ print.printer }}</div>
    </td>
    <td class="px-4 py-2"><JobStateBadge :state="print.state" /></td>
    <td class="hidden px-4 py-2 text-zinc-400 md:table-cell">{{ formatDateTime(print.started_at) }}</td>
    <td class="px-4 py-2 text-zinc-300 tabular-nums">{{ formatDuration(print.elapsed) }}</td>
    <td class="hidden px-4 py-2 text-zinc-300 tabular-nums lg:table-cell">{{ formatFilament(print.filament_g, print.filament_mm) }}</td>
    <td class="hidden max-w-48 px-4 py-2 xl:table-cell">
      <SpoolPicker :spool="print.spool" :model-value="print.spool?.id ?? null" @update:model-value="emit('spool', $event)" />
    </td>
    <td class="hidden px-4 py-2 text-zinc-300 tabular-nums lg:table-cell">{{ formatEnergy(print.energy_wh) }}</td>
    <td class="px-4 py-2">
      <div class="flex justify-end gap-1">
        <IconButton v-if="postcard" icon="photo" title="Postcard" @click="emit('open')" />
        <IconButton v-else-if="opens" icon="camera" title="Timelapse" @click="emit('open')" />
        <IconButton v-if="print.file" icon="play" title="Print again" :disabled="!printable" class="text-emerald-400" @click="emit('print')" />
        <IconButton icon="trash" title="Delete" class="hover:text-red-400" @click="emit('remove')" />
      </div>
    </td>
  </tr>
</template>
