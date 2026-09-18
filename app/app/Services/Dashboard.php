<?php

namespace App\Services;

use App\Models\User;

/**
 * The widget catalog and the per-user dashboard layout from config/dashboard.php.
 */
class Dashboard
{
    /**
     * @return array<string, array{title: string, description: string, w: int, h: int, min_w: int, min_h: int, needs_connection: bool}>
     */
    public function widgets(): array
    {
        return config('dashboard.widgets', []);
    }

    /**
     * @return list<string>
     */
    public function types(): array
    {
        return array_keys($this->widgets());
    }

    public function columns(): int
    {
        return (int) config('dashboard.columns', 12);
    }

    /**
     * @return list<array{i: string, type: string, x: int, y: int, w: int, h: int}>
     */
    public function defaultLayout(): array
    {
        return array_values(config('dashboard.default', []));
    }

    /**
     * @return list<array{i: string, type: string, x: int, y: int, w: int, h: int}>
     */
    public function layoutFor(User $user): array
    {
        $layout = $user->dashboard;

        return is_array($layout) ? array_values($layout) : $this->defaultLayout();
    }
}
