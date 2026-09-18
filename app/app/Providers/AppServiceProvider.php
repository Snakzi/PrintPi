<?php

namespace App\Providers;

use App\Services\Settings;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\ServiceProvider;
use Laravel\Passkeys\Passkeys;
use Throwable;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        // The passkey endpoints live under /api/v1 with the session guard, see routes/api.php.
        Passkeys::ignoreRoutes();
    }

    public function boot(): void
    {
        $this->applyTimezoneFromSettings();
    }

    /**
     * The timezone chosen during setup applies to every request; before the
     * database exists this silently keeps the configured default.
     */
    private function applyTimezoneFromSettings(): void
    {
        try {
            if (! Schema::hasTable('settings')) {
                return;
            }
            $timezone = $this->app->make(Settings::class)->get('timezone');
        } catch (Throwable) {
            return;
        }

        if (is_string($timezone) && in_array($timezone, timezone_identifiers_list(), true)) {
            config(['app.timezone' => $timezone]);
            date_default_timezone_set($timezone);
        }
    }
}
