<?php

namespace App\Services;

use App\Models\Spool;

/**
 * Starts the daemon's filament walkthrough with everything it needs: the temperature of
 * the material going in and of the one coming out, the moves of the configured printer
 * profile and the spool the inventory books once the filament is in.
 */
class FilamentChange
{
    /** Hot enough to pull out anything that is usually printed when nobody knows what is loaded. */
    public const int UNKNOWN_UNLOAD_NOZZLE = 230;

    public function __construct(
        private readonly PrinterBridge $bridge,
        private readonly FilamentInventory $inventory,
        private readonly Settings $settings,
        private readonly PrinterCatalog $catalog,
    ) {}

    /**
     * Load a spool of the inventory, or a material that is not in it; with unloadFirst the
     * filament still in the printer comes out first.
     */
    public function load(?Spool $spool, ?string $material, bool $unloadFirst): void
    {
        $material = $spool?->material ?? $material;
        $nozzle = self::nozzleFor($material);
        $this->bridge->startFilament(
            $unloadFirst ? 'change' : 'load',
            $spool === null ? null : ['id' => $spool->id, 'name' => $spool->name, 'material' => $spool->material, 'color' => $spool->color],
            $material,
            $nozzle,
            $unloadFirst ? $this->unloadNozzle($nozzle) : null,
            $this->moves(),
        );
    }

    public function unload(): void
    {
        $loaded = $this->inventory->loaded();
        $this->bridge->startFilament('unload', null, $loaded?->material, null, $this->unloadNozzle(null), $this->moves());
    }

    /**
     * The nozzle temperature for a material: the catalog's entry, else the entry the name
     * starts with ("PLA Silk" heats like PLA), else the default for the unknown.
     */
    public static function nozzleFor(?string $material): int
    {
        $entry = self::materialEntry($material);

        return (int) ($entry['nozzle'] ?? config('filament.default_nozzle', 220));
    }

    /**
     * Whether the catalog knows the material's temperature, so the UI can say when it guesses.
     */
    public static function knowsMaterial(?string $material): bool
    {
        return self::materialEntry($material) !== null;
    }

    /**
     * @return array<string, mixed>|null
     */
    private static function materialEntry(?string $material): ?array
    {
        $wanted = strtoupper(trim((string) $material));
        if ($wanted === '') {
            return null;
        }
        $materials = config('filament.materials', []);
        if (isset($materials[$wanted])) {
            return $materials[$wanted];
        }
        $best = null;
        foreach ($materials as $name => $entry) {
            if (str_starts_with($wanted, strtoupper($name)) && ($best === null || strlen($name) > strlen($best))) {
                $best = $name;
            }
        }

        return $best === null ? null : $materials[$best];
    }

    /**
     * What is in the printer comes out at its own temperature: the loaded spool's material,
     * else the higher of the new filament's and a figure that gets the usual materials out.
     */
    private function unloadNozzle(?int $incoming): int
    {
        $loaded = $this->inventory->loaded();
        if ($loaded !== null) {
            return self::nozzleFor($loaded->material);
        }

        return max((int) $incoming, self::UNKNOWN_UNLOAD_NOZZLE);
    }

    /**
     * The configured profile's load, purge and unload moves; null leaves the daemon its defaults.
     *
     * @return array<string, mixed>|null
     */
    private function moves(): ?array
    {
        $id = $this->settings->get('printer_profile');
        $profile = is_string($id) ? $this->catalog->find($id) : null;

        return is_array($profile['filament'] ?? null) ? $profile['filament'] : null;
    }
}
