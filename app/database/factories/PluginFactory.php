<?php

namespace Database\Factories;

use App\Models\Plugin;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<Plugin>
 */
class PluginFactory extends Factory
{
    /**
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'id' => fake()->unique()->slug(2),
            'source' => Plugin::SOURCE_BUILTIN,
            'url' => null,
            'version' => '1.0.0',
            'enabled' => true,
            'settings' => [],
        ];
    }

    public function fromGit(string $url = 'https://github.com/example/printpi-plugin'): static
    {
        return $this->state(fn (): array => ['source' => Plugin::SOURCE_GIT, 'url' => $url]);
    }

    public function disabled(): static
    {
        return $this->state(fn (): array => ['enabled' => false]);
    }
}
