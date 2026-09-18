<script setup>
import { useDashboardStore } from '../../stores/dashboard';
import { useToastStore } from '../../stores/toasts';
import { widgetIcon } from '../../widgets';
import AppButton from '../AppButton.vue';
import { useConfirm } from '../../composables/useConfirm';
import DropdownItem from '../DropdownItem.vue';
import DropdownMenu from '../DropdownMenu.vue';

const dashboard = useDashboardStore();
const toasts = useToastStore();
const confirm = useConfirm();

async function reset() {
  if (!(await confirm('Reset the dashboard to the default layout?'))) return;
  try {
    await dashboard.reset();
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <template v-if="dashboard.editing">
      <DropdownMenu align="left" menu-class="w-72">
        <template #trigger="{ toggle }">
          <AppButton size="sm" icon="plus" :disabled="!dashboard.available.length" @click="toggle">Add widget</AppButton>
        </template>
        <DropdownItem v-for="widget in dashboard.available" :key="widget.type" :icon="widgetIcon(widget.type)" @click="dashboard.add(widget.type)">
          <span class="flex min-w-0 flex-col">
            <span>{{ widget.title }}</span>
            <span class="truncate text-xs text-zinc-500">{{ widget.description }}</span>
          </span>
        </DropdownItem>
      </DropdownMenu>
      <AppButton size="sm" icon="refresh" @click="reset">Reset layout</AppButton>
      <span v-if="dashboard.saving" class="text-xs text-zinc-500">Saving…</span>
      <span v-else-if="dashboard.error" class="text-xs text-red-400">{{ dashboard.error }}</span>
      <AppButton size="sm" variant="primary" icon="check" class="ml-auto" @click="dashboard.editing = false">Done</AppButton>
    </template>
    <AppButton v-else size="sm" icon="settings" class="ml-auto" @click="dashboard.editing = true">Customize</AppButton>
  </div>
</template>
