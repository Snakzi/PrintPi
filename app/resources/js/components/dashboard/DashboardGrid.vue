<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { GridLayout, GridItem } from 'grid-layout-plus';
import { useDashboardStore } from '../../stores/dashboard';
import { widgetFor, widgetIcon } from '../../widgets';
import WidgetFrame from './WidgetFrame.vue';

const dashboard = useDashboardStore();
const ROW_HEIGHT = 40;
const GAP = 12;

const clone = (layout) => layout.map((item) => ({ ...item }));
const layout = ref(clone(dashboard.layout));

// Add, remove and reset replace the store's array; drag and resize come back
// through layout-updated, so only adopt store changes that differ from ours.
watch(
  () => dashboard.layout,
  (next) => {
    const mine = JSON.stringify(layout.value.map(({ i, x, y, w, h }) => ({ i, x, y, w, h })));
    const theirs = JSON.stringify(next.map(({ i, x, y, w, h }) => ({ i, x, y, w, h })));
    if (mine !== theirs) layout.value = clone(next);
  },
);

function onLayoutUpdated(updated) {
  dashboard.setLayout(updated);
}

// Below the md breakpoint the widgets stack in reading order instead of a grid.
const query = window.matchMedia('(min-width: 768px)');
const wide = ref(query.matches);
const onChange = (event) => (wide.value = event.matches);
onMounted(() => query.addEventListener('change', onChange));
onUnmounted(() => query.removeEventListener('change', onChange));

const stacked = computed(() => [...layout.value].sort((a, b) => a.y - b.y || a.x - b.x));

// Stacked widgets size to their content unless the registry pins them to their grid height.
function stackedStyle(item) {
  return widgetFor(item.type)?.fixed ? { height: `${item.h * ROW_HEIGHT + (item.h - 1) * GAP}px` } : undefined;
}
</script>

<template>
  <!-- The grid puts its item gap outside the outer widgets as well; pull it back so they line up with the toolbar. -->
  <div v-if="wide" class="-m-3">
  <GridLayout
    v-model:layout="layout"
    :col-num="dashboard.columns"
    :row-height="ROW_HEIGHT"
    :margin="[GAP, GAP]"
    :is-draggable="dashboard.editing"
    :is-resizable="dashboard.editing"
    :vertical-compact="true"
    :use-css-transforms="true"
    @layout-updated="onLayoutUpdated"
  >
    <GridItem
      v-for="item in layout"
      :key="item.i"
      :i="item.i"
      :x="item.x"
      :y="item.y"
      :w="item.w"
      :h="item.h"
      :min-w="dashboard.meta(item.type).min_w"
      :min-h="dashboard.meta(item.type).min_h"
      drag-allow-from=".widget-drag-handle"
      drag-ignore-from="button, input, select, textarea, a"
    >
      <WidgetFrame
        :item="item"
        :meta="dashboard.meta(item.type)"
        :icon="widgetIcon(item.type)"
        :editing="dashboard.editing"
        @remove="dashboard.remove(item.i)"
      >
        <component :is="widgetFor(item.type)?.component" v-bind="widgetFor(item.type)?.props ?? {}" />
      </WidgetFrame>
    </GridItem>
  </GridLayout>
  </div>

  <div v-else class="flex flex-col gap-3">
    <WidgetFrame
      v-for="item in stacked"
      :key="item.i"
      :item="item"
      :meta="dashboard.meta(item.type)"
      :icon="widgetIcon(item.type)"
      :editing="dashboard.editing"
      :style="stackedStyle(item)"
      @remove="dashboard.remove(item.i)"
    >
      <component :is="widgetFor(item.type)?.component" v-bind="widgetFor(item.type)?.props ?? {}" />
    </WidgetFrame>
  </div>
</template>
