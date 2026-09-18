<?php

/*
| Widgets the dashboard can show. Sizes are grid units on a 12-column grid,
| one row is 40 px high. "needs_connection" widgets show a placeholder until a
| printer is connected. The frontend registry in resources/js/widgets/index.js
| must know every type listed here.
*/

$widget = static fn (
    string $title,
    string $description,
    int $w,
    int $h,
    int $minW,
    int $minH,
    bool $needsConnection,
): array => [
    'title' => $title,
    'description' => $description,
    'w' => $w,
    'h' => $h,
    'min_w' => $minW,
    'min_h' => $minH,
    'needs_connection' => $needsConnection,
];

return [
    'columns' => 12,

    'widgets' => [
        'temperatures' => $widget('Temperatures', 'Hotend and bed with presets', 6, 6, 3, 4, true),
        'chart' => $widget('Temperature history', 'Last ten minutes as a chart', 6, 7, 4, 5, true),
        'job' => $widget('Print job', 'The part, progress, times and controls of the print', 3, 11, 3, 5, false),
        'live_preview' => $widget('Live preview', 'The running print in 3D', 6, 8, 4, 5, false),
        'printer_info' => $widget('Printer', 'Connection, firmware and port', 3, 6, 3, 4, false),
        'motion' => $widget('Motion', 'Jog and home the axes', 6, 5, 4, 5, true),
        'extruder' => $widget('Extruder', 'Extrude and retract filament', 3, 4, 3, 3, true),
        'fan_speed' => $widget('Fan & speed', 'Part fan, speed and flow', 3, 4, 3, 3, true),
        'terminal' => $widget('Terminal', 'Send G-code and read replies', 6, 8, 4, 5, true),
        'camera' => $widget('Camera', 'Live view', 6, 8, 3, 4, false),
        'files' => $widget('Files', 'Recently uploaded G-code', 4, 6, 3, 4, false),
        'system' => $widget('System', 'Load, memory and temperature of the Pi', 3, 6, 3, 4, false),
        'macros' => $widget('Quick commands', 'Your own G-code buttons', 3, 5, 2, 3, true),
        'plugins' => $widget('Plugins', 'Controls of the enabled plugins', 3, 5, 3, 3, false),
        'filament' => $widget('Filament', 'The loaded spool and what is left of it', 3, 5, 3, 4, false),
    ],

    'default' => [
        ['i' => 'temperatures', 'type' => 'temperatures', 'x' => 0, 'y' => 0, 'w' => 6, 'h' => 6],
        ['i' => 'job', 'type' => 'job', 'x' => 6, 'y' => 0, 'w' => 3, 'h' => 11],
        ['i' => 'printer_info', 'type' => 'printer_info', 'x' => 9, 'y' => 0, 'w' => 3, 'h' => 6],
        ['i' => 'chart', 'type' => 'chart', 'x' => 0, 'y' => 6, 'w' => 6, 'h' => 7],
        ['i' => 'plugins', 'type' => 'plugins', 'x' => 9, 'y' => 6, 'w' => 3, 'h' => 5],
        ['i' => 'motion', 'type' => 'motion', 'x' => 6, 'y' => 11, 'w' => 6, 'h' => 5],
        ['i' => 'live_preview', 'type' => 'live_preview', 'x' => 0, 'y' => 13, 'w' => 6, 'h' => 8],
        ['i' => 'camera', 'type' => 'camera', 'x' => 6, 'y' => 16, 'w' => 6, 'h' => 8],
        ['i' => 'terminal', 'type' => 'terminal', 'x' => 0, 'y' => 21, 'w' => 6, 'h' => 8],
        ['i' => 'filament', 'type' => 'filament', 'x' => 6, 'y' => 24, 'w' => 3, 'h' => 5],
    ],
];
