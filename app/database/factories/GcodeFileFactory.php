<?php

namespace Database\Factories;

use App\Models\GcodeFile;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<GcodeFile>
 */
class GcodeFileFactory extends Factory
{
    /**
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'name' => fake()->unique()->slug(2).'.gcode',
            'size' => fake()->numberBetween(10_000, 50_000_000),
            'metadata' => [
                'slicer' => 'PrusaSlicer 2.8.1',
                'estimated_seconds' => fake()->numberBetween(600, 36_000),
                'filament_mm' => fake()->randomFloat(1, 500, 50_000),
                'filament_g' => fake()->randomFloat(2, 1, 150),
                'layer_height' => 0.2,
                'nozzle_temperature' => 215,
                'bed_temperature' => 60,
            ],
            'thumbnail' => null,
        ];
    }
}
