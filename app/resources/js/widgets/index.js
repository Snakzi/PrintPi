/**
 * Widget registry: maps the types from config/dashboard.php to components and icons.
 * Titles, sizes and the connection requirement come from the API so both
 * sides stay in sync; this file only knows how to render a type. `fixed` widgets
 * keep their grid height when the dashboard stacks on a narrow screen, the others
 * size to their content there.
 */
import TemperaturePanel from '../components/TemperaturePanel.vue';
import TemperatureChart from '../components/TemperatureChart.vue';
import JobPanel from '../components/JobPanel.vue';
import Terminal from '../components/Terminal.vue';
import MotionPanel from '../components/widgets/MotionPanel.vue';
import ExtruderPanel from '../components/widgets/ExtruderPanel.vue';
import FanSpeedPanel from '../components/widgets/FanSpeedPanel.vue';
import CameraWidget from '../components/widgets/CameraWidget.vue';
import FilesWidget from '../components/widgets/FilesWidget.vue';
import PrinterInfoWidget from '../components/widgets/PrinterInfoWidget.vue';
import SystemWidget from '../components/widgets/SystemWidget.vue';
import MacrosWidget from '../components/widgets/MacrosWidget.vue';
import PluginsWidget from '../components/widgets/PluginsWidget.vue';
import LivePreviewWidget from '../components/widgets/LivePreviewWidget.vue';
import FilamentWidget from '../components/widgets/FilamentWidget.vue';

export const WIDGETS = {
  temperatures: { component: TemperaturePanel, icon: 'fire', props: { embedded: true } },
  chart: { component: TemperatureChart, icon: 'trending', fixed: true, props: { embedded: true } },
  job: { component: JobPanel, icon: 'layers', props: { embedded: true } },
  live_preview: { component: LivePreviewWidget, icon: 'cube', fixed: true },
  printer_info: { component: PrinterInfoWidget, icon: 'printer' },
  motion: { component: MotionPanel, icon: 'move' },
  extruder: { component: ExtruderPanel, icon: 'nozzle' },
  fan_speed: { component: FanSpeedPanel, icon: 'gauge' },
  terminal: { component: Terminal, icon: 'terminal', fixed: true, props: { embedded: true } },
  camera: { component: CameraWidget, icon: 'camera', fixed: true },
  files: { component: FilesWidget, icon: 'folder' },
  system: { component: SystemWidget, icon: 'chip' },
  macros: { component: MacrosWidget, icon: 'bolt' },
  plugins: { component: PluginsWidget, icon: 'puzzle' },
  filament: { component: FilamentWidget, icon: 'spool' },
};

export function widgetFor(type) {
  return WIDGETS[type] ?? null;
}

export function widgetIcon(type) {
  return WIDGETS[type]?.icon ?? 'grid';
}
