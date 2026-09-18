<?php

namespace Database\Factories;

use App\Models\Spool;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<Spool>
 */
class SpoolFactory extends Factory
{
    /**
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'name' => fake()->unique()->colorName(),
            'vendor' => fake()->randomElement(['Prusament', 'Polymaker', 'Bambu Lab', 'eSun']),
            'material' => 'PLA',
            'color' => fake()->hexColor(),
            'finish' => null,
            'diameter' => 1.75,
            'density' => 1.24,
            'weight' => 1000.0,
            'spool_weight' => 190.0,
            'used' => fake()->randomFloat(2, 0, 600),
            'price' => 29.99,
            'loaded' => false,
            'archived_at' => null,
        ];
    }

    public function loaded(): static
    {
        return $this->state(fn (): array => ['loaded' => true]);
    }

    public function archived(): static
    {
        return $this->state(fn (): array => ['archived_at' => now()->subDay(), 'loaded' => false]);
    }
}
