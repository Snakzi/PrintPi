<script setup>
import { onMounted, ref } from 'vue';
import { useFilamentStore } from '../../stores/filament';
import { usePrinterStore } from '../../stores/printer';
import { usePrintStore } from '../../stores/prints';
import { useSettingsStore } from '../../stores/settings';
import { useToastStore } from '../../stores/toasts';
import { useStartPrint } from '../../composables/useStartPrint';
import PostcardModal from './PostcardModal.vue';
import { useConfirm } from '../../composables/useConfirm';
import PrintHistoryRow from './PrintHistoryRow.vue';

const prints = usePrintStore();
const settings = useSettingsStore();
const printer = usePrinterStore();
const filament = useFilamentStore();
const toasts = useToastStore();
const confirm = useConfirm();
const { startPrint } = useStartPrint();
const opened = ref(null);

// The spool column needs the inventory for its picker.
onMounted(() => filament.ensure().catch(() => {}));

async function changeSpool(print, spoolId) {
  try {
    await prints.setSpool(print, spoolId);
    await filament.load();
  } catch (error) {
    toasts.error(error.message);
  }
}

async function remove(print) {
  if (!(await confirm(`Delete the print of ${print.name}?`, { message: 'Its postcard and timelapse go with it.', danger: true }))) return;
  try {
    await prints.remove(print);
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <div class="overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-900">
    <table class="w-full text-left text-sm">
      <thead class="text-xs tracking-wide text-zinc-500 uppercase">
        <tr>
          <th class="w-16 px-2 py-3" />
          <th class="px-4 py-3 font-medium">Print</th>
          <th class="px-4 py-3 font-medium">Outcome</th>
          <th class="hidden px-4 py-3 font-medium md:table-cell">Started</th>
          <th class="px-4 py-3 font-medium">Duration</th>
          <th class="hidden px-4 py-3 font-medium lg:table-cell">Filament</th>
          <th class="hidden px-4 py-3 font-medium xl:table-cell">Spool</th>
          <th class="hidden px-4 py-3 font-medium lg:table-cell">Energy</th>
          <th class="px-4 py-3" />
        </tr>
      </thead>
      <tbody>
        <tr v-if="prints.loading && !prints.items.length">
          <td colspan="9" class="px-4 py-6 text-center text-zinc-500">Loading …</td>
        </tr>
        <tr v-else-if="!prints.items.length">
          <td colspan="9" class="px-4 py-6 text-center text-zinc-500">No prints yet.</td>
        </tr>
        <PrintHistoryRow
          v-for="print in prints.items"
          :key="print.id"
          :print="print"
          :printable="printer.connected && !printer.printing"
          :postcard="settings.values.postcard !== false"
          @open="opened = print"
          @print="startPrint(print.file)"
          @spool="changeSpool(print, $event)"
          @remove="remove(print)"
        />
      </tbody>
    </table>
    <PostcardModal v-if="opened" :print="opened" :card="settings.values.postcard !== false" @close="opened = null" />
  </div>
</template>
