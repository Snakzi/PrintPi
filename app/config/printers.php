<?php

/*
| Printer profiles offered during setup. "type" picks the illustration
| (bedslinger, cube, delta, custom); a photo dropped into
| public/images/printers/<id>.png is used instead when present.
| "supported" false marks machines PrintPi cannot drive yet (no Marlin over USB).
| "firmware_family" is the token Prusa puts into its release asset names (MK4S in
| MK4_MK4S_MK3.9_MK3.9S_firmware_6.5.7.bbf), so the firmware card can find updates.
| "filament" holds the moves of the filament walkthrough as [mm, mm/min] lists: "load"
| pushes the filament from the gears to the nozzle (slow while the user holds it, then
| fast), "purge" is the one move that flushes the old colour out, "unload" shapes the
| tip and pulls the filament clear of the gears. Prusa's are its firmware's own numbers.
*/

// A direct drive extruder: the nozzle is a few centimetres below the gears.
$direct = [
    'load' => [[30, 360], [50, 1200]],
    'purge' => [40, 180],
    'unload' => [[5, 600], [-20, 3000], [-80, 1500]],
];
// A bowden tube between the extruder and the hotend, about 40 cm on the usual machines.
$bowden = [
    'load' => [[40, 600], [400, 3000]],
    'purge' => [50, 180],
    'unload' => [[5, 600], [-20, 3000], [-450, 3000]],
];
// MK4/S and XL, Buddy 6.5.7. Ramming already retracts the entire unload length.
$nextruder = [
    'load' => [[30, 324], [50, 1080]],
    'purge' => [27, 162],
    'unload' => [[8, 995], [-43, 6000], [-8, 3000], [-4, 1800], [20, 600], [-20, 470], [55, 1740], [-55, 6000], [20, 340], [-20, 210], [-50, 2000]],
];
$coreOne = ['load' => [[40, 360], [20, 1500]], 'purge' => [40, 180]] + $nextruder;
// The MK3 family's extruder, with the ramming Buddy uses on the MK3.5.
$mk3 = [
    'load' => [[30, 324], [50, 1080]],
    'purge' => [21, 162],
    'unload' => [[7, 1500], [-50, 2700], [-5, 50], [-50, 1500], [-105, 1620]],
];
// The MINI's bowden extruder.
$mini = [
    'load' => [[40, 600], [320, 4800]],
    'purge' => [50, 180],
    'unload' => [[20, 1500], [-50, 2700], [-5, 50], [-50, 1500], [-400, 4800]],
];

$printer = static fn (
    string $id,
    string $manufacturer,
    string $model,
    string $type,
    ?array $bed,
    int $baud = 115200,
    string $firmware = 'marlin',
    ?string $note = null,
    bool $supported = true,
    ?string $family = null,
    ?array $filament = null,
): array => [
    'id' => $id,
    'manufacturer' => $manufacturer,
    'model' => $model,
    'type' => $type,
    'bed' => $bed,
    'baud_rate' => $baud,
    'firmware' => $firmware,
    'note' => $note,
    'supported' => $supported,
    'firmware_family' => $family,
    'filament' => $filament ?? $direct,
];

return [
    'models' => [
        $printer('prusa-mk4s', 'Prusa Research', 'Original Prusa MK4S', 'bedslinger', ['x' => 250, 'y' => 210, 'z' => 220], 115200, 'buddy', family: 'MK4S', filament: $nextruder),
        $printer('prusa-mk4', 'Prusa Research', 'Original Prusa MK4', 'bedslinger', ['x' => 250, 'y' => 210, 'z' => 220], 115200, 'buddy', family: 'MK4', filament: $nextruder),
        $printer('prusa-mk3s', 'Prusa Research', 'Original Prusa i3 MK3S+', 'bedslinger', ['x' => 250, 'y' => 210, 'z' => 210], 115200, 'prusa', family: 'MK3S', filament: $mk3),
        $printer('prusa-mini', 'Prusa Research', 'Original Prusa MINI+', 'bedslinger', ['x' => 180, 'y' => 180, 'z' => 180], 115200, 'buddy', family: 'MINI', filament: $mini),
        $printer('prusa-core-one', 'Prusa Research', 'Prusa CORE One', 'cube', ['x' => 250, 'y' => 220, 'z' => 270], 115200, 'buddy', family: 'COREONE', filament: $coreOne),
        $printer('prusa-xl', 'Prusa Research', 'Original Prusa XL', 'cube', ['x' => 360, 'y' => 360, 'z' => 360], 115200, 'buddy', family: 'XL', filament: $nextruder),
        $printer('creality-ender-3', 'Creality', 'Ender-3 / Pro', 'bedslinger', ['x' => 220, 'y' => 220, 'z' => 250], filament: $bowden),
        $printer('creality-ender-3-v2', 'Creality', 'Ender-3 V2 / Neo', 'bedslinger', ['x' => 220, 'y' => 220, 'z' => 250], filament: $bowden),
        $printer('creality-ender-3-s1', 'Creality', 'Ender-3 S1 / Pro', 'bedslinger', ['x' => 220, 'y' => 220, 'z' => 270]),
        $printer('creality-ender-3-v3-se', 'Creality', 'Ender-3 V3 SE', 'bedslinger', ['x' => 220, 'y' => 220, 'z' => 250]),
        $printer('creality-ender-5', 'Creality', 'Ender-5 / Pro', 'cube', ['x' => 220, 'y' => 220, 'z' => 300], filament: $bowden),
        $printer('creality-cr-10', 'Creality', 'CR-10 / CR-10S', 'bedslinger', ['x' => 300, 'y' => 300, 'z' => 400], filament: $bowden),
        $printer('anycubic-kobra-2', 'Anycubic', 'Kobra 2', 'bedslinger', ['x' => 220, 'y' => 220, 'z' => 250]),
        $printer('anycubic-vyper', 'Anycubic', 'Vyper', 'bedslinger', ['x' => 245, 'y' => 245, 'z' => 260], filament: $bowden),
        $printer('anycubic-i3-mega', 'Anycubic', 'i3 Mega / Mega S', 'bedslinger', ['x' => 210, 'y' => 210, 'z' => 205], 250000, filament: $bowden),
        $printer('anycubic-kossel', 'Anycubic', 'Kossel Linear Plus', 'delta', ['x' => 230, 'y' => 230, 'z' => 300], filament: $bowden),
        $printer('elegoo-neptune-3', 'Elegoo', 'Neptune 3 / Pro', 'bedslinger', ['x' => 225, 'y' => 225, 'z' => 280], filament: $bowden),
        $printer('artillery-sidewinder-x2', 'Artillery', 'Sidewinder X2', 'bedslinger', ['x' => 300, 'y' => 300, 'z' => 400], 250000),
        $printer('artillery-genius', 'Artillery', 'Genius / Pro', 'bedslinger', ['x' => 220, 'y' => 220, 'z' => 250], 250000),
        $printer('sovol-sv06', 'Sovol', 'SV06', 'bedslinger', ['x' => 220, 'y' => 220, 'z' => 250]),
        $printer('sovol-sv06-plus', 'Sovol', 'SV06 Plus', 'bedslinger', ['x' => 300, 'y' => 300, 'z' => 340]),
        $printer('flsun-qq-s-pro', 'FLSUN', 'QQ-S Pro', 'delta', ['x' => 255, 'y' => 255, 'z' => 360], filament: $bowden),
        $printer('custom', 'Other', 'Marlin printer', 'custom', null, 115200, 'marlin', 'Any printer with Marlin firmware over USB'),
        $printer('klipper', 'Other', 'Klipper printer', 'cube', null, 115200, 'klipper', 'Comes with the Moonraker backend', false),
    ],
];
