<?php

/*
| What the spool form offers. Materials carry their typical density in g/cm³,
| which turns the length a slicer reports into grams when the file carries no
| weight. Vendors carry the weight of their empty spool in g where it is known
| and their product lines: one entry per colour with the material, the colour
| as the vendor sells it, the net weight when it is not a kilogram and the
| finish where the filament has one (`glitter`), so a Galaxy Black is drawn
| with its sparkle. All of it is only a starting point the user can overwrite
| on every spool; colours are approximations of the vendors' swatches.
*/

$palette = [
    'Black' => '#141414', 'White' => '#f4f4f2', 'Grey' => '#8a8d90', 'Light Grey' => '#c9cbcd', 'Dark Grey' => '#4a4d50',
    'Space Grey' => '#3f4248', 'Anthracite' => '#3a3d40', 'Graphite' => '#4b4e52', 'Silver' => '#b8bcc0', 'Gold' => '#d4a53a',
    'Copper' => '#b87333', 'Bronze' => '#8c6a3f', 'Red' => '#c62828', 'Dark Red' => '#8b1e2b', 'Orange' => '#f0741e',
    'Yellow' => '#f2c80f', 'Green' => '#2e8b45', 'Dark Green' => '#1f5f38', 'Light Green' => '#8bc34a', 'Blue' => '#1e4fa3',
    'Light Blue' => '#79b8e6', 'Sky Blue' => '#5fb3e8', 'Dark Blue' => '#16305f', 'Navy' => '#12275c', 'Purple' => '#6a4aa8',
    'Pink' => '#ee6fa0', 'Magenta' => '#d81b8c', 'Cyan' => '#20a7c9', 'Teal' => '#1f8a8a', 'Brown' => '#6d4c35',
    'Beige' => '#e4d3b3', 'Bone White' => '#e9e3d3', 'Warm White' => '#f4efe4', 'Cold White' => '#f2f5f7', 'Natural' => '#e6dfcf',
    'Transparent' => '#d9e6ea', 'Clear' => '#d9e6ea', 'Skin' => '#f1c9a5', 'Olive' => '#7a7a3a', 'Rainbow' => '#8e44ad',
];

/**
 * A product line whose colours come from the shared palette.
 *
 * @param  list<string>  $colours
 * @return list<array{line: string, name: string, material: string, color: string, weight?: int}>
 */
$line = static fn (string $line, string $material, array $colours, ?int $weight = null): array => array_map(
    static fn (string $colour): array => ['line' => $line, 'name' => $colour, 'material' => $material, 'color' => $palette[$colour]]
        + ($weight === null ? [] : ['weight' => $weight]),
    $colours,
);

/**
 * A product line with the vendor's own colour names and swatches. `$finish` is
 * the finish of the whole line, or a map of the colour names that have one.
 *
 * @param  array<string, string>  $colours  name => hex
 * @param  string|array<string, string>  $finish
 * @return list<array{line: string, name: string, material: string, color: string, weight?: int, finish?: string}>
 */
$named = static fn (string $line, string $material, array $colours, ?int $weight = null, string|array $finish = []): array => array_map(
    static fn (string $name, string $hex): array => ['line' => $line, 'name' => $name, 'material' => $material, 'color' => $hex]
        + ($weight === null ? [] : ['weight' => $weight])
        + (is_string($finish) ? ['finish' => $finish] : (isset($finish[$name]) ? ['finish' => $finish[$name]] : [])),
    array_keys($colours),
    $colours,
);

$basics = ['Black', 'White', 'Grey', 'Red', 'Blue', 'Orange', 'Yellow', 'Green', 'Purple', 'Pink'];
// Prusament's sparkling colours, the same names across its lines.
$galaxy = array_fill_keys(['Galaxy Black', 'Galaxy Silver', 'Galaxy Purple', 'Oh My Gold', 'Viva la Bronze', 'Mystic Brown'], 'glitter');
$silk = ['Gold', 'Silver', 'Copper', 'Red', 'Blue', 'Green', 'Purple', 'Rainbow'];
$petg = ['Black', 'White', 'Grey', 'Transparent', 'Red', 'Blue', 'Green', 'Orange', 'Yellow'];
$tpu = ['Black', 'White', 'Red', 'Blue', 'Transparent'];

return [
    // Density in g/cm³, and the nozzle and bed temperature the filament walkthrough heats to, in °C.
    'materials' => [
        'PLA' => ['density' => 1.24, 'nozzle' => 215, 'bed' => 60],
        'PETG' => ['density' => 1.27, 'nozzle' => 230, 'bed' => 85],
        'PCTG' => ['density' => 1.23, 'nozzle' => 250, 'bed' => 85],
        'ABS' => ['density' => 1.04, 'nozzle' => 255, 'bed' => 100],
        'ASA' => ['density' => 1.07, 'nozzle' => 260, 'bed' => 100],
        'TPU' => ['density' => 1.21, 'nozzle' => 230, 'bed' => 50],
        'PA' => ['density' => 1.14, 'nozzle' => 285, 'bed' => 100],
        'PC' => ['density' => 1.20, 'nozzle' => 275, 'bed' => 100],
        'PLA-CF' => ['density' => 1.25, 'nozzle' => 230, 'bed' => 60],
        'PETG-CF' => ['density' => 1.29, 'nozzle' => 250, 'bed' => 85],
        'PA-CF' => ['density' => 1.20, 'nozzle' => 270, 'bed' => 100],
        'PVB' => ['density' => 1.10, 'nozzle' => 215, 'bed' => 75],
        'PP' => ['density' => 0.90, 'nozzle' => 240, 'bed' => 100],
        'HIPS' => ['density' => 1.04, 'nozzle' => 220, 'bed' => 100],
        'PVA' => ['density' => 1.23, 'nozzle' => 215, 'bed' => 60],
    ],

    // The temperature for a material the list does not know.
    'default_nozzle' => 220,

    // The surface effects a spool can carry; every one of them has its own drawing in the UI.
    'finishes' => ['glitter'],

    'vendors' => [
        'Prusament' => [
            'spool_weight' => 190,
            'products' => [
                ...$named('PLA', 'PLA', [
                    'Galaxy Black' => '#26262e', 'Jet Black' => '#0f0f10', 'Prusa Orange' => '#f26a2a', 'Vanilla White' => '#efe9dc',
                    'Pearl Mouse' => '#b7b3ad', 'Gravity Grey' => '#6f7175', 'Galaxy Silver' => '#a9abb0', 'Lipstick Red' => '#c41e3a',
                    'Royal Blue' => '#1a3d8f', 'Azure Blue' => '#2e86de', 'Galaxy Purple' => '#4b3a7a', 'Ms. Pink' => '#e5559a',
                    'Jungle Green' => '#1f7a4d', 'Simply Green' => '#4caf50', 'Pineapple Yellow' => '#f4c430', 'Oh My Gold' => '#c9a24b',
                    'Viva la Bronze' => '#8a5a3c', 'Mystic Brown' => '#5b3a29', 'Army Green' => '#4b5320',
                ], null, $galaxy),
                ...$named('PETG', 'PETG', [
                    'Jet Black' => '#0f0f10', 'Galaxy Black' => '#26262e', 'Prusa Orange' => '#f26a2a', 'Signal White' => '#f3f3f1',
                    'Urban Grey' => '#8b8f94', 'Anthracite Grey' => '#3a3d40', 'Clear' => '#d9e4e8', 'Carmine Red Transparent' => '#b3202e',
                    'Ultramarine Blue Transparent' => '#2540a8', 'Neon Green Transparent' => '#7fd63a', 'Chalky Blue' => '#7fa9c9',
                    'Terracotta Light' => '#c9714f',
                ], null, $galaxy),
                ...$named('ASA', 'ASA', [
                    'Prusa Orange' => '#f26a2a', 'Jet Black' => '#0f0f10', 'Galaxy Black' => '#26262e', 'Natural' => '#e8e2d3',
                    'Signal White' => '#f3f3f1', 'Sapphire Blue' => '#1f4fa3', 'Lipstick Red' => '#c41e3a',
                ], 850, $galaxy),
                ...$named('PC Blend', 'PC', ['Jet Black' => '#0f0f10', 'Natural' => '#e6e0d2', 'Urban Grey' => '#8b8f94'], 970),
                ...$named('PVB', 'PVB', [
                    'Clear' => '#dfe7ea', 'Yellow Transparent' => '#f0d24a', 'Bright Green Transparent' => '#6ccf5a',
                    'Dark Blue Transparent' => '#22357a', 'Orange Transparent' => '#f08a3a',
                ], 500),
            ],
        ],
        'Bambu Lab' => [
            'spool_weight' => 250,
            'products' => [
                ...$named('PLA Basic', 'PLA', [
                    'Jade White' => '#f4f4f0', 'Black' => '#101010', 'Gray' => '#8e9089', 'Silver' => '#a6a9aa', 'Light Gray' => '#d1d3d5',
                    'Dark Gray' => '#545454', 'Red' => '#c12e1f', 'Maroon Red' => '#9d2235', 'Orange' => '#ff6a13', 'Pumpkin Orange' => '#ff9016',
                    'Yellow' => '#f4ee2a', 'Sunflower Yellow' => '#fec600', 'Bambu Green' => '#00ae42', 'Mistletoe Green' => '#3f8e43',
                    'Bright Green' => '#a3d34a', 'Blue' => '#0a2989', 'Cyan' => '#0086d6', 'Cobalt Blue' => '#0056b8', 'Turquoise' => '#00b1b7',
                    'Purple' => '#5e43b7', 'Indigo Purple' => '#482960', 'Pink' => '#f55a74', 'Hot Pink' => '#f5547c', 'Magenta' => '#ec008c',
                    'Brown' => '#9d432c', 'Cocoa Brown' => '#6f5034', 'Beige' => '#e8dbb7', 'Gold' => '#e4bd68', 'Bronze' => '#847d48',
                ]),
                ...$named('PLA Matte', 'PLA', [
                    'Ivory White' => '#f6f3ea', 'Charcoal' => '#1d1d1d', 'Ash Gray' => '#9b9ea0', 'Nardo Gray' => '#757575', 'Latte Brown' => '#d3b7a7',
                    'Caramel' => '#ae835b', 'Dark Brown' => '#7d6556', 'Sakura Pink' => '#e8afcf', 'Lilac Purple' => '#ae96d4', 'Plum' => '#950051',
                    'Marine Blue' => '#0078bf', 'Ice Blue' => '#a3d8e1', 'Dark Blue' => '#042f56', 'Grass Green' => '#61c680', 'Dark Green' => '#68724d',
                    'Scarlet Red' => '#de4343', 'Dark Red' => '#bb3d43', 'Terracotta' => '#b15533', 'Lemon Yellow' => '#f7d959',
                    'Mandarin Orange' => '#f99963', 'Desert Tan' => '#d6c3a0', 'Bone White' => '#cbc6b8',
                ]),
                ...$named('PLA Silk+', 'PLA', [
                    'Gold' => '#e5b74a', 'Silver' => '#c0c2c4', 'Titan Gray' => '#6e7073', 'Blue' => '#2f6fd6', 'Red' => '#c8352b',
                    'Purple' => '#7f4bb8', 'Champagne' => '#e6d6b5',
                ]),
                ...$named('PLA Wood', 'PLA', [
                    'Black Walnut' => '#4a3a2c', 'Rosewood' => '#6e3f37', 'Classic Birch' => '#d7c3a3', 'White Oak' => '#e2d6bd',
                ]),
                ...$named('PLA Sparkle', 'PLA', [
                    'Onyx Black Sparkle' => '#2a2a2f', 'Crimson Red Sparkle' => '#9d2b2f', 'Royal Purple Sparkle' => '#5b3f8a',
                    'Alpine Green Sparkle' => '#3f7a5a', 'Slate Gray Sparkle' => '#5f6368', 'Classic Gold Sparkle' => '#b8912f',
                ], null, 'glitter'),
                ...$named('PLA Galaxy', 'PLA', [
                    'Nebulae' => '#4a4d66', 'Brown' => '#6e4b3a', 'Green' => '#3d6b55', 'Purple' => '#5a4a86', 'Red' => '#8c3a40',
                ], null, 'glitter'),
                ...$named('PLA-CF', 'PLA-CF', [
                    'Black' => '#1a1a1a', 'Burgundy Red' => '#7a2c2c', 'Matcha Green' => '#8fb15a', 'Lava Gray' => '#4b4d4f',
                    'Iris Blue' => '#4b6ea8', 'Jeans Blue' => '#62778f',
                ]),
                ...$named('PETG HF', 'PETG', [
                    'Black' => '#101010', 'White' => '#f4f4f4', 'Gray' => '#adb1b2', 'Dark Gray' => '#545454', 'Blue' => '#0f4fa0',
                    'Lake Blue' => '#6a9ec2', 'Red' => '#ba2a24', 'Green' => '#1d9a5c', 'Forest Green' => '#2b5e44', 'Lime Green' => '#b3e300',
                    'Yellow' => '#f2b900', 'Orange' => '#f75403', 'Peanut Brown' => '#a97c58', 'Cream' => '#f5ecd3',
                ]),
                ...$named('PETG Translucent', 'PETG', [
                    'Gray' => '#9ea3a7', 'Olive' => '#9aa25c', 'Teal' => '#4aa3a0', 'Purple' => '#9a7fc7', 'Brown' => '#a0754f', 'Pink' => '#e6a0b8',
                ]),
                ...$named('PETG-CF', 'PETG-CF', [
                    'Black' => '#1a1a1a', 'Brick Red' => '#8b3a2f', 'Titan Gray' => '#5d6165', 'Indigo Blue' => '#3d4f7c',
                    'Malachite Green' => '#2f7d5f', 'Violet Purple' => '#7e5aa2',
                ]),
                ...$named('ABS', 'ABS', [
                    'Black' => '#101010', 'White' => '#f4f4f4', 'Silver' => '#a6a9aa', 'Bambu Green' => '#00ae42', 'Red' => '#c12e1f',
                    'Blue' => '#0a2989', 'Navy Blue' => '#0c2340', 'Orange' => '#ff6a13', 'Tangerine Yellow' => '#f9b300', 'Olive' => '#6f6b46',
                    'Azure' => '#48a4d0',
                ]),
                ...$named('ASA', 'ASA', ['Black' => '#101010', 'White' => '#f4f4f4', 'Gray' => '#8e9089', 'Red' => '#c12e1f', 'Blue' => '#0a2989']),
                ...$named('TPU 95A HF', 'TPU', [
                    'Black' => '#101010', 'White' => '#f4f4f4', 'Gray' => '#8e9089', 'Red' => '#c12e1f', 'Blue' => '#0a2989', 'Yellow' => '#f4ee2a',
                ]),
                ...$named('PAHT-CF', 'PA-CF', ['Black' => '#1c1c1c']),
            ],
        ],
        'Polymaker' => [
            'spool_weight' => 140,
            'products' => [
                ...$named('PolyTerra PLA', 'PLA', [
                    'Charcoal Black' => '#2a2a2a', 'Cotton White' => '#f2f2f2', 'Fossil Grey' => '#8c8c8c', 'Army Green' => '#4b5a3f',
                    'Lava Red' => '#c0392b', 'Sapphire Blue' => '#1f4e9c', 'Sunrise Orange' => '#f28c28', 'Savannah Yellow' => '#f2c94c',
                    'Forest Green' => '#2f6b3a', 'Lavender Purple' => '#8e7cc3', 'Peach' => '#f4b183', 'Arctic Teal' => '#5fb8b3',
                    'Muted White' => '#e8e6e0', 'Muted Blue' => '#6b8fb5', 'Muted Green' => '#7fa37a', 'Muted Red' => '#b5595a',
                ]),
                ...$line('PolyLite PLA', 'PLA', ['Black', 'White', 'Grey', 'Red', 'Blue', 'Orange', 'Yellow', 'Green', 'Purple', 'Teal', 'Natural']),
                ...$line('PolyLite PLA Pro', 'PLA', ['Black', 'White', 'Grey', 'Red', 'Blue']),
                ...$line('PolyLite PETG', 'PETG', ['Black', 'White', 'Grey', 'Clear', 'Red', 'Blue', 'Orange', 'Yellow', 'Green']),
                ...$line('PolyLite ASA', 'ASA', ['Black', 'White', 'Grey', 'Red', 'Blue']),
                ...$line('PolyFlex TPU95', 'TPU', ['Black', 'White', 'Red', 'Blue'], 750),
            ],
        ],
        'eSUN' => [
            'spool_weight' => 220,
            'products' => [
                ...$line('PLA+', 'PLA', [...$basics, 'Silver', 'Gold', 'Brown', 'Magenta', 'Cyan', 'Light Blue', 'Bone White', 'Warm White', 'Cold White', 'Olive', 'Skin']),
                ...$line('ePLA-Matte', 'PLA', [...$basics, 'Beige']),
                ...$line('eSilk PLA', 'PLA', $silk),
                ...$line('PETG', 'PETG', [...$petg, 'Purple']),
                ...$line('ABS+', 'ABS', ['Black', 'White', 'Grey', 'Red', 'Blue']),
                ...$line('eTPU-95A', 'TPU', [...$tpu, 'Yellow']),
                ...$line('ePA-CF', 'PA-CF', ['Black']),
            ],
        ],
        'SUNLU' => [
            'spool_weight' => 135,
            'products' => [
                ...$line('PLA', 'PLA', [...$basics, 'Skin', 'Brown', 'Silver', 'Gold', 'Transparent']),
                ...$line('PLA+', 'PLA', $basics),
                ...$line('PLA Matte', 'PLA', $basics),
                ...$line('PLA Silk', 'PLA', $silk),
                ...$line('PETG', 'PETG', $petg),
                ...$line('TPU', 'TPU', $tpu),
                ...$line('ABS', 'ABS', ['Black', 'White', 'Grey']),
            ],
        ],
        'Overture' => [
            'spool_weight' => 140,
            'products' => [
                ...$line('PLA', 'PLA', ['Black', 'White', 'Space Grey', 'Light Grey', 'Red', 'Blue', 'Orange', 'Yellow', 'Green', 'Purple', 'Pink', 'Brown', 'Sky Blue', 'Dark Green', 'Beige', 'Bone White', 'Gold', 'Silver', 'Transparent']),
                ...$line('PLA Matte', 'PLA', $basics),
                ...$line('Silk PLA', 'PLA', ['Gold', 'Silver', 'Copper', 'Rainbow', 'Red', 'Blue']),
                ...$line('PETG', 'PETG', ['Black', 'White', 'Space Grey', 'Transparent', 'Red', 'Blue', 'Green', 'Orange', 'Yellow', 'Purple']),
                ...$line('TPU', 'TPU', $tpu),
                ...$line('ABS', 'ABS', ['Black', 'White', 'Grey']),
            ],
        ],
        'Hatchbox' => [
            'spool_weight' => 245,
            'products' => [
                ...$line('PLA', 'PLA', [...$basics, 'Silver', 'Gold', 'Brown', 'Transparent', 'Sky Blue']),
                ...$line('PETG', 'PETG', $petg),
                ...$line('ABS', 'ABS', ['Black', 'White', 'Grey', 'Red', 'Blue']),
                ...$line('TPU', 'TPU', ['Black', 'White', 'Red']),
            ],
        ],
        'Fiberlogy' => [
            'spool_weight' => null,
            'products' => [
                ...$line('Easy PLA', 'PLA', [...$basics, 'Graphite', 'Brown', 'Navy', 'Natural', 'Silver', 'Gold'], 850),
                ...$line('Easy PET-G', 'PETG', ['Black', 'White', 'Graphite', 'Grey', 'Transparent', 'Red', 'Blue', 'Green', 'Yellow', 'Orange', 'Navy'], 850),
                ...$line('FiberFlex 40D', 'TPU', ['Black', 'White', 'Red', 'Blue'], 850),
                ...$line('ASA', 'ASA', ['Black', 'White', 'Grey'], 750),
                ...$line('Nylon PA12', 'PA', ['Black', 'Natural'], 750),
            ],
        ],
        'Extrudr' => [
            'spool_weight' => null,
            'products' => [
                ...$line('PLA NX2', 'PLA', [...$basics, 'Anthracite', 'Silver', 'Gold', 'Brown', 'Beige']),
                ...$line('PETG', 'PETG', [...$petg, 'Anthracite']),
                ...$line('DuraPro ASA', 'ASA', ['Black', 'White', 'Grey', 'Anthracite', 'Red', 'Blue']),
                ...$line('Flex Medium', 'TPU', ['Black', 'White', 'Red']),
            ],
        ],
        'Spectrum' => [
            'spool_weight' => null,
            'products' => [
                ...$named('PLA Premium', 'PLA', [
                    'Deep Black' => '#121212', 'Polar White' => '#f5f5f5', 'Dark Grey' => '#4a4d50', 'Silver Star' => '#b8bcc0',
                    'Bloody Red' => '#b71c1c', 'Navy Blue' => '#12275c', 'Pacific Blue' => '#1f6fb5', 'Lion Orange' => '#f28c28',
                    'Bahama Yellow' => '#f5d33a', 'Forest Green' => '#2f6b3a', 'Lilac' => '#b39ddb', 'Pink Panther' => '#f48fb1',
                ]),
                ...$named('PET-G Premium', 'PETG', [
                    'Deep Black' => '#121212', 'Arctic White' => '#f5f5f5', 'Silver Star' => '#b8bcc0', 'Dark Grey' => '#4a4d50',
                    'Glassy' => '#d9e6ea', 'Transparent Red' => '#c62828', 'Transparent Blue' => '#1e4fa3', 'Transparent Green' => '#2e8b45',
                    'Transparent Yellow' => '#f2c80f', 'Navy Blue' => '#12275c', 'Lion Orange' => '#f28c28',
                ]),
                ...$named('ASA 275', 'ASA', ['Deep Black' => '#121212', 'Polar White' => '#f5f5f5', 'Dark Grey' => '#4a4d50', 'Bloody Red' => '#b71c1c', 'Navy Blue' => '#12275c']),
                ...$named('PLA Pro', 'PLA', ['Deep Black' => '#121212', 'Polar White' => '#f5f5f5', 'Dark Grey' => '#4a4d50']),
            ],
        ],
        'Formfutura' => [
            'spool_weight' => null,
            'products' => [
                ...$line('EasyFil PLA', 'PLA', [...$basics, 'Silver', 'Brown', 'Gold', 'Natural'], 750),
                ...$line('EasyFil PET', 'PETG', ['Black', 'White', 'Clear', 'Red', 'Blue', 'Green', 'Grey'], 750),
                ...$line('ApolloX', 'ASA', ['Black', 'White', 'Grey', 'Red', 'Blue'], 750),
                ...$line('ReForm rPLA', 'PLA', ['Black', 'White', 'Grey'], 750),
                ...$line('Python Flex', 'TPU', ['Black', 'White'], 500),
            ],
        ],
        'Das Filament' => [
            'spool_weight' => null,
            'products' => [
                ...$line('PLA', 'PLA', [...$basics, 'Brown', 'Silver', 'Gold', 'Natural', 'Transparent', 'Anthracite', 'Beige', 'Dark Blue', 'Light Blue', 'Dark Green', 'Light Green']),
                ...$line('PETG', 'PETG', [...$petg, 'Anthracite']),
                ...$line('ABS', 'ABS', ['Black', 'White', 'Grey', 'Red', 'Blue']),
                ...$line('TPU', 'TPU', ['Black', 'White', 'Red']),
            ],
        ],
        '3DJake' => [
            'spool_weight' => null,
            'products' => [
                ...$line('ecoPLA', 'PLA', [...$basics, 'Brown', 'Silver', 'Gold', 'Natural', 'Dark Blue', 'Light Blue', 'Dark Green', 'Beige']),
                ...$line('ecoPLA Matt', 'PLA', ['Black', 'White', 'Grey', 'Red', 'Blue', 'Green', 'Yellow']),
                ...$line('PETG', 'PETG', ['Black', 'White', 'Grey', 'Clear', 'Red', 'Blue', 'Green', 'Orange', 'Yellow']),
                ...$line('niceABS', 'ABS', ['Black', 'White', 'Grey', 'Red', 'Blue']),
                ...$line('TPU A95', 'TPU', ['Black', 'White', 'Red', 'Blue']),
            ],
        ],
        'AzureFilm' => [
            'spool_weight' => null,
            'products' => [
                ...$line('PLA', 'PLA', [...$basics, 'Brown', 'Silver', 'Gold', 'Natural', 'Transparent', 'Dark Blue', 'Light Blue', 'Dark Green', 'Skin']),
                ...$line('PLA Silk', 'PLA', [...$silk, 'Bronze']),
                ...$line('PETG', 'PETG', $petg),
                ...$line('ASA', 'ASA', ['Black', 'White', 'Grey']),
                ...$line('TPU 98A', 'TPU', ['Black', 'White', 'Red']),
            ],
        ],
        'Creality' => [
            'spool_weight' => null,
            'products' => [
                ...$line('Hyper PLA', 'PLA', [...$basics, 'Skin', 'Silver', 'Gold']),
                ...$line('Ender-PLA', 'PLA', ['Black', 'White', 'Grey', 'Red', 'Blue', 'Orange', 'Yellow', 'Green']),
                ...$line('Hyper PETG', 'PETG', $petg),
                ...$line('Hyper ABS', 'ABS', ['Black', 'White', 'Grey']),
                ...$line('CR-TPU', 'TPU', $tpu),
                ...$line('Hyper PLA-CF', 'PLA-CF', ['Black']),
            ],
        ],
        'Anycubic' => [
            'spool_weight' => null,
            'products' => [
                ...$line('PLA', 'PLA', [...$basics, 'Silver', 'Gold', 'Brown', 'Transparent', 'Skin', 'Dark Blue', 'Light Blue', 'Dark Green']),
                ...$line('High Speed PLA', 'PLA', ['Black', 'White', 'Grey', 'Red', 'Blue', 'Green', 'Yellow', 'Orange']),
                ...$line('PLA Silk', 'PLA', ['Gold', 'Silver', 'Copper', 'Red', 'Blue', 'Rainbow']),
                ...$line('PETG', 'PETG', ['Black', 'White', 'Grey', 'Transparent', 'Red', 'Blue', 'Green']),
                ...$line('ABS', 'ABS', ['Black', 'White', 'Grey']),
                ...$line('TPU', 'TPU', ['Black', 'White', 'Red']),
            ],
        ],
        'Elegoo' => [
            'spool_weight' => null,
            'products' => [
                ...$line('PLA', 'PLA', [...$basics, 'Silver', 'Gold', 'Brown', 'Transparent', 'Skin', 'Dark Blue', 'Light Blue', 'Dark Green', 'Beige', 'Space Grey']),
                ...$line('Rapid PLA+', 'PLA', $basics),
                ...$line('PLA Matte', 'PLA', $basics),
                ...$line('PLA Silk', 'PLA', $silk),
                ...$line('PETG', 'PETG', $petg),
                ...$line('Rapid PETG', 'PETG', ['Black', 'White', 'Grey', 'Transparent', 'Red', 'Blue']),
                ...$line('ABS', 'ABS', ['Black', 'White', 'Grey']),
                ...$line('TPU 95A', 'TPU', $tpu),
            ],
        ],
    ],

    'default_diameter' => 1.75,
];
