<?php

namespace App\Models;

use Database\Factories\SpoolFactory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

/**
 * A spool of filament in the inventory. `weight` is the net filament weight when
 * new and `used` what the prints booked on it consumed, both in grams; at most one
 * spool is `loaded` in the printer and receives the next prints. `finish` names a
 * surface effect from the filament catalog (`glitter`) or is null for a plain one.
 */
class Spool extends Model
{
    /** @use HasFactory<SpoolFactory> */
    use HasFactory;

    protected $fillable = [
        'name', 'vendor', 'material', 'color', 'finish', 'diameter', 'density', 'weight', 'spool_weight', 'used',
        'price', 'loaded', 'archived_at',
    ];

    /** @var array<string, mixed> */
    protected $attributes = [
        'diameter' => 1.75,
        'density' => 1.24,
        'weight' => 1000.0,
        'used' => 0.0,
        'loaded' => false,
    ];

    /**
     * @return HasMany<PrintJob, $this>
     */
    public function printJobs(): HasMany
    {
        return $this->hasMany(PrintJob::class);
    }

    /**
     * Grams left on the spool; a spool that consumed more than it held reads as empty.
     */
    public function remaining(): float
    {
        return max(0.0, round($this->weight - $this->used, 2));
    }

    public function isArchived(): bool
    {
        return $this->archived_at !== null;
    }

    /**
     * The mass of a length of this filament, from its diameter and density.
     */
    public function gramsFor(float $millimetres): float
    {
        return round($millimetres * $this->crossSection() * $this->density / 1000, 2);
    }

    /**
     * The length of a mass of this filament, the inverse of gramsFor().
     */
    public function millimetresFor(float $grams): float
    {
        $section = $this->crossSection();
        if ($section <= 0 || $this->density <= 0) {
            return 0.0;
        }

        return round($grams * 1000 / ($section * $this->density), 1);
    }

    /**
     * The filament's cross section in mm².
     */
    private function crossSection(): float
    {
        return M_PI * ($this->diameter / 2) ** 2;
    }

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'diameter' => 'float',
            'density' => 'float',
            'weight' => 'float',
            'spool_weight' => 'float',
            'used' => 'float',
            'price' => 'float',
            'loaded' => 'boolean',
            'archived_at' => 'datetime',
        ];
    }
}
