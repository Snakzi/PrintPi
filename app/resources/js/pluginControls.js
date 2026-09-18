import { defineAsyncComponent } from 'vue';
import PluginControl from './components/PluginControl.vue';

/* Control types that take a whole section on the plugin page instead of a row in the
   panel. Each component takes the props of PluginControl and emits change with a value
   for the control's action, or act with { action, value } for one of its extra actions. */
export const PANELS = {
  mesh: defineAsyncComponent(() => import('./components/BedMeshControl.vue')),
  devices: defineAsyncComponent(() => import('./components/DevicesControl.vue')),
};

/* Panel types with a compact form for the dashboard widget; the others stay on their page. */
export const ROWS = {
  devices: defineAsyncComponent(() => import('./components/DeviceSwitches.vue')),
};

export const isPanel = (control) => control.type in PANELS;

export const inlineControls = (plugin) => plugin.controls.filter((control) => !isPanel(control));

export const panelControls = (plugin) => plugin.controls.filter(isPanel);

export const dashboardControls = (plugin) => plugin.controls.filter((control) => !isPanel(control) || control.type in ROWS);

export const controlComponent = (control, compact = false) =>
  (compact && ROWS[control.type]) || PANELS[control.type] || PluginControl;
