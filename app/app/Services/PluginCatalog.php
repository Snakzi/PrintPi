<?php

namespace App\Services;

use App\Exceptions\PluginException;
use App\Models\Plugin;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Log;

/**
 * Finds plugin directories: the built-in ones shipped in the repository and the
 * ones cloned from git into the installed directory. A directory counts when it
 * holds a valid plugin.json whose id matches the directory name.
 */
class PluginCatalog
{
    /**
     * @return array<string, array{manifest: PluginManifest, path: string, source: string}>
     */
    public function discover(): array
    {
        $found = [];
        $directories = [
            Plugin::SOURCE_BUILTIN => $this->builtinDirectory(),
            Plugin::SOURCE_GIT => $this->installedDirectory(),
        ];
        foreach ($directories as $source => $directory) {
            foreach ($this->manifestsIn($directory) as $path => $manifest) {
                if (isset($found[$manifest->id])) {
                    Log::warning("Plugin {$manifest->id} in {$path} shadows a built-in plugin, ignoring it.");

                    continue;
                }
                $found[$manifest->id] = ['manifest' => $manifest, 'path' => $path, 'source' => $source];
            }
        }

        return $found;
    }

    /**
     * @return array{manifest: PluginManifest, path: string, source: string}
     */
    public function find(string $id): array
    {
        return $this->discover()[$id] ?? throw new PluginException("Plugin {$id} does not exist.", 404);
    }

    public function builtinDirectory(): string
    {
        return (string) config('printpi.plugins.builtin');
    }

    public function installedDirectory(): string
    {
        $directory = (string) config('printpi.plugins.installed');
        File::ensureDirectoryExists($directory);

        return $directory;
    }

    /**
     * @return array<string, PluginManifest> keyed by the plugin's real path
     */
    private function manifestsIn(string $directory): array
    {
        $manifests = [];
        foreach (glob(rtrim($directory, '/').'/*/plugin.json') ?: [] as $file) {
            $path = dirname($file);
            try {
                $manifest = PluginManifest::fromDirectory($path);
            } catch (PluginException $exception) {
                Log::warning("Ignoring plugin in {$path}: {$exception->getMessage()}");

                continue;
            }
            if ($manifest->id !== basename($path)) {
                Log::warning("Ignoring plugin in {$path}: the directory is not named {$manifest->id}.");

                continue;
            }
            $manifests[(string) realpath($path)] = $manifest;
        }
        ksort($manifests);

        return $manifests;
    }
}
