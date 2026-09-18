<script setup>
import { onMounted, onUnmounted } from 'vue';
import { RouterLink } from 'vue-router';
import { usePluginStore } from '../../stores/plugins';
import { dashboardControls } from '../../pluginControls';
import AppButton from '../AppButton.vue';
import IconButton from '../IconButton.vue';
import PluginPanel from '../PluginPanel.vue';
import WidgetActions from '../dashboard/WidgetActions.vue';
import WidgetEmpty from '../dashboard/WidgetEmpty.vue';

const plugins = usePluginStore();

onMounted(() => plugins.startPolling());
onUnmounted(() => plugins.stopPolling());
</script>

<template>
  <div class="flex h-full flex-col">
    <WidgetActions>
      <IconButton icon="arrow-up-right" title="All plugins" :to="{ name: 'plugins' }" />
    </WidgetActions>

    <div v-if="plugins.withControls.length" class="flex flex-col divide-y divide-zinc-800/80">
      <PluginPanel
        v-for="plugin in plugins.withControls"
        :key="plugin.id"
        :plugin="plugin"
        :controls="dashboardControls(plugin)"
        embedded
        compact
        class="py-3 first:pt-0 last:pb-0"
      />
    </div>
    <WidgetEmpty v-else-if="plugins.loaded" icon="puzzle" message="No plugin controls">
      <RouterLink v-slot="{ navigate }" :to="{ name: 'plugins' }" custom>
        <AppButton size="sm" variant="ghost" icon="puzzle" @click="navigate">Plugins</AppButton>
      </RouterLink>
    </WidgetEmpty>
    <WidgetEmpty v-else icon="puzzle" message="Loading…" />
  </div>
</template>
