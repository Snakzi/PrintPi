<?php

namespace App\Console\Commands;

use App\Services\PluginManager;
use Illuminate\Console\Attributes\Description;
use Illuminate\Console\Attributes\Signature;
use Illuminate\Console\Command;

#[Signature('printpi:sync-plugins')]
#[Description('Hand the enabled plugins with their settings to the daemon')]
class SyncPlugins extends Command
{
    /**
     * A deploy can change a built-in plugin's manifest, and the daemon only learns about that
     * when the app writes the plugin list again; install.sh runs this after every deploy.
     */
    public function handle(PluginManager $plugins): int
    {
        $plugins->sync();
        $this->info('Plugins synced.');

        return self::SUCCESS;
    }
}
