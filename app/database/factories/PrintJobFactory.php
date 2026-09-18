<?php

namespace Database\Factories;

use App\Models\PrintJob;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<PrintJob>
 */
class PrintJobFactory extends Factory
{
    /**
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        $elapsed = fake()->numberBetween(600, 36_000);
        $started = fake()->dateTimeBetween('-30 days', '-1 hour');

        return [
            'key' => fake()->unique()->regexify('[a-f0-9]{12}'),
            'gcode_file_id' => null,
            'name' => fake()->unique()->slug(2).'.gcode',
            'state' => 'finished',
            'error' => null,
            'started_at' => $started,
            'finished_at' => (clone $started)->modify("+{$elapsed} seconds"),
            'elapsed' => $elapsed,
            'progress' => 1.0,
            'layers' => 120,
            'total_layers' => 120,
            'filament_g' => fake()->randomFloat(2, 1, 150),
            'filament_mm' => fake()->randomFloat(1, 500, 50_000),
            'slicer' => 'PrusaSlicer 2.8.1',
            'printer' => 'Original Prusa MK4S',
            'thumbnail' => null,
            'cover' => null,
            'timelapse' => null,
            'video' => null,
            'frames' => 0,
            'energy_wh' => fake()->randomFloat(1, 20, 900),
        ];
    }

    public function cancelled(): static
    {
        return $this->state(fn (): array => ['state' => 'cancelled', 'progress' => 0.4, 'layers' => 48]);
    }

    public function failed(string $error = 'printer disconnected'): static
    {
        return $this->state(fn (): array => ['state' => 'error', 'error' => $error, 'progress' => 0.2, 'layers' => 24]);
    }
}
