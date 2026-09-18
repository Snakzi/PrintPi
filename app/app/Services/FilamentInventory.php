<?php

namespace App\Services;

use App\Models\PrintJob;
use App\Models\Spool;
use Illuminate\Support\Facades\DB;

/**
 * The spool inventory: which spool is in the printer and what the prints took
 * from it. A print is booked on the spool loaded when it was filed and can be
 * moved to another one later, the grams follow it.
 */
class FilamentInventory
{
    public function __construct(private readonly PrinterBridge $bridge) {}

    /**
     * Books what the daemon's filament walkthrough put into the printer or took out since the
     * last poll: a spool from the inventory becomes the loaded one, filament without a spool or
     * an unload leaves nothing loaded.
     */
    public function sync(): void
    {
        foreach ($this->bridge->takeFilamentEvents() as $event) {
            $spool = $event['event'] === 'loaded' && isset($event['spool']['id']) ? Spool::query()->find($event['spool']['id']) : null;
            if ($spool instanceof Spool) {
                $this->load($spool);
            } else {
                $this->unload();
            }
        }
    }

    public function loaded(): ?Spool
    {
        return Spool::query()->where('loaded', true)->first();
    }

    /**
     * A new spool; the material's typical density and a full spool are the defaults.
     *
     * @param  array<string, mixed>  $data  validated SpoolRequest input
     */
    public function create(array $data): Spool
    {
        $spool = new Spool([
            'diameter' => config('filament.default_diameter'),
            'density' => self::densityOf((string) ($data['material'] ?? '')),
        ]);

        return $this->fill($spool, $data);
    }

    /**
     * @param  array<string, mixed>  $data  validated SpoolRequest input
     */
    public function update(Spool $spool, array $data): Spool
    {
        return $this->fill($spool, $data);
    }

    /**
     * The typical density of a material the config knows, else PLA's.
     */
    public static function densityOf(string $material): float
    {
        return (float) (config('filament.materials.'.strtoupper($material).'.density') ?? 1.24);
    }

    /**
     * @param  array<string, mixed>  $data
     */
    private function fill(Spool $spool, array $data): Spool
    {
        $spool->fill(array_intersect_key($data, array_flip(
            ['name', 'vendor', 'material', 'color', 'finish', 'diameter', 'density', 'weight', 'spool_weight', 'price'],
        )));
        if (array_key_exists('remaining', $data)) {
            $spool->used = max(0.0, $spool->weight - (float) $data['remaining']);
        } elseif (! $spool->exists) {
            $spool->used = 0.0;
        }
        if (array_key_exists('archived', $data)) {
            $spool->archived_at = $data['archived'] ? ($spool->archived_at ?? now()) : null;
            if ($data['archived']) {
                $spool->loaded = false;
            }
        }
        $spool->save();

        return $spool;
    }

    /**
     * Puts the spool into the printer; the one loaded before is taken out, an archived spool comes back.
     */
    public function load(Spool $spool): Spool
    {
        DB::transaction(function () use ($spool): void {
            Spool::query()->where('loaded', true)->whereKeyNot($spool->id)->update(['loaded' => false]);
            $spool->forceFill(['loaded' => true, 'archived_at' => null])->save();
        });

        return $spool;
    }

    public function unload(): void
    {
        Spool::query()->where('loaded', true)->update(['loaded' => false]);
    }

    /**
     * Books the print on a spool, or on none: what it consumed leaves the spool it
     * was on and lands on the new one.
     */
    public function assign(PrintJob $job, ?Spool $spool): void
    {
        DB::transaction(function () use ($job, $spool): void {
            $previous = $job->spool;
            if ($previous?->id === $spool?->id) {
                return;
            }
            if ($previous !== null) {
                $previous->forceFill(['used' => max(0.0, $previous->used - $this->gramsOf($job, $previous))])->save();
            }
            if ($spool !== null) {
                $spool->forceFill(['used' => $spool->used + $this->gramsOf($job, $spool)])->save();
            }
            $job->spool()->associate($spool)->save();
        });
    }

    /**
     * What the print took from a spool: the grams the slicer reported, else its length converted.
     */
    public function gramsOf(PrintJob $job, Spool $spool): float
    {
        if ($job->filament_g !== null) {
            return $job->filament_g;
        }

        return $job->filament_mm !== null ? $spool->gramsFor($job->filament_mm) : 0.0;
    }
}
