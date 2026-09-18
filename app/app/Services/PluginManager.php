<?php

namespace App\Services;

use App\Exceptions\PluginException;
use App\Models\Plugin;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Validator;
use Illuminate\Support\Str;

/**
 * Install state and settings of plugins, and what the daemon gets to run.
 *
 * The catalog finds the directories, the plugins table records which of them are
 * installed with which settings, and every change ends in sync(), which hands the
 * enabled plugins with their settings to the daemon through Redis.
 */
class PluginManager
{
    public function __construct(
        private readonly PluginCatalog $catalog,
        private readonly PrinterBridge $bridge,
        private readonly GitCloner $git,
    ) {}

    /**
     * @return list<array<string, mixed>>
     */
    public function all(): array
    {
        $rows = Plugin::query()->get()->keyBy('id');
        $statuses = $this->bridge->pluginStatuses();
        $plugins = [];
        foreach ($this->catalog->discover() as $id => $entry) {
            $plugins[] = $this->describe($entry, $rows->get($id), $statuses[$id] ?? null);
        }

        return $plugins;
    }

    /**
     * @return array<string, mixed>
     */
    public function show(string $id): array
    {
        $entry = $this->catalog->find($id);

        return $this->describe($entry, Plugin::query()->find($id), $this->bridge->pluginStatuses()[$id] ?? null);
    }

    /**
     * Install a plugin the catalog already knows, which is every built-in one.
     *
     * @return array<string, mixed>
     */
    public function install(string $id): array
    {
        $entry = $this->catalog->find($id);
        if (Plugin::query()->whereKey($id)->exists()) {
            throw new PluginException("Plugin {$id} is already installed.");
        }
        Plugin::query()->create([
            'id' => $id,
            'source' => $entry['source'],
            'version' => $entry['manifest']->version,
            'enabled' => true,
            'settings' => $entry['manifest']->defaults(),
        ]);
        $this->sync();

        return $this->show($id);
    }

    /**
     * Clone a repository into a scratch directory and keep it only once its manifest checks out.
     *
     * @return array<string, mixed>
     */
    public function installFromGit(string $url): array
    {
        $directory = $this->catalog->installedDirectory();
        $scratch = $directory.'/.clone-'.Str::random(8);
        try {
            $this->git->clone($url, $scratch);
            $manifest = PluginManifest::fromDirectory($scratch);
            $target = $directory.'/'.$manifest->id;
            if (isset($this->catalog->discover()[$manifest->id]) || is_dir($target)) {
                throw new PluginException("A plugin with the id {$manifest->id} already exists.");
            }
            File::move($scratch, $target);
        } catch (PluginException $exception) {
            File::deleteDirectory($scratch);

            throw $exception;
        }
        Plugin::query()->create([
            'id' => $manifest->id,
            'source' => Plugin::SOURCE_GIT,
            'url' => $url,
            'version' => $manifest->version,
            'enabled' => true,
            'settings' => $manifest->defaults(),
        ]);
        $this->sync();

        return $this->show($manifest->id);
    }

    /**
     * Pull a git plugin and pick up its new manifest; built-in plugins update with PrintPi.
     *
     * @return array<string, mixed>
     */
    public function upgrade(string $id): array
    {
        $row = $this->row($id);
        if ($row->source !== Plugin::SOURCE_GIT) {
            throw new PluginException("Plugin {$id} is built in and updates with PrintPi.");
        }
        $entry = $this->catalog->find($id);
        $this->git->pull($entry['path']);
        $manifest = PluginManifest::fromDirectory($entry['path']);
        $row->update(['version' => $manifest->version, 'settings' => $this->settingsOf($manifest, $row)]);
        $this->sync();

        return $this->show($id);
    }

    public function uninstall(string $id): void
    {
        $row = $this->row($id);
        $path = $this->catalog->discover()[$id]['path'] ?? null;
        $row->delete();
        $installed = (string) realpath($this->catalog->installedDirectory());
        if ($row->source === Plugin::SOURCE_GIT && $path !== null && $installed !== '' && Str::startsWith($path, $installed.'/')) {
            File::deleteDirectory($path);
        }
        $this->bridge->forgetPlugin($id);
        $this->sync();
    }

    /**
     * @return array<string, mixed>
     */
    public function setEnabled(string $id, bool $enabled): array
    {
        $this->row($id)->update(['enabled' => $enabled]);
        $this->sync();

        return $this->show($id);
    }

    /**
     * @param  array<string, mixed>  $input
     * @return array<string, mixed>
     */
    public function updateSettings(string $id, array $input): array
    {
        $row = $this->row($id);
        $manifest = $this->catalog->find($id)['manifest'];
        $validated = Validator::make($input, $manifest->rules())->validate();
        $row->update(['settings' => array_merge($this->settingsOf($manifest, $row), $manifest->normalize($validated))]);
        $this->sync();

        return $this->show($id);
    }

    public function action(string $id, string $action, mixed $value): void
    {
        $row = $this->row($id);
        $manifest = $this->catalog->find($id)['manifest'];
        if (! $row->enabled) {
            throw new PluginException("Plugin {$id} is disabled.");
        }
        if (! $manifest->hasAction($action)) {
            throw new PluginException("Plugin {$id} has no action {$action}.");
        }
        $this->bridge->pluginAction($id, $action, $value);
    }

    /**
     * Tell the daemon which plugins to run, with their settings.
     */
    public function sync(): void
    {
        $discovered = $this->catalog->discover();
        $specs = [];
        foreach (Plugin::query()->where('enabled', true)->orderBy('id')->get() as $row) {
            $entry = $discovered[$row->id] ?? null;
            if ($entry === null || ! $entry['manifest']->daemon) {
                continue;
            }
            $specs[] = [
                'id' => $row->id,
                'path' => $entry['path'],
                'version' => $entry['manifest']->version,
                'settings' => $this->settingsOf($entry['manifest'], $row),
            ];
        }
        $this->bridge->syncPlugins($specs);
    }

    private function row(string $id): Plugin
    {
        return Plugin::query()->find($id) ?? throw new PluginException("Plugin {$id} is not installed.", 404);
    }

    /**
     * @return array<string, mixed>
     */
    private function settingsOf(PluginManifest $manifest, ?Plugin $row): array
    {
        return $manifest->normalize(array_merge($manifest->defaults(), $row?->settings ?? []));
    }

    /**
     * @param  array{manifest: PluginManifest, path: string, source: string}  $entry
     * @param  array<string, mixed>|null  $daemon
     * @return array<string, mixed>
     */
    private function describe(array $entry, ?Plugin $row, ?array $daemon): array
    {
        $manifest = $entry['manifest'];

        return [
            ...$manifest->toArray(),
            'source' => $entry['source'],
            'url' => $row?->url,
            'installed' => $row !== null,
            'enabled' => (bool) $row?->enabled,
            'settings' => $this->settingsOf($manifest, $row),
            'daemon' => $row?->enabled
                ? ($daemon ?? ['state' => 'pending', 'error' => null, 'version' => null, 'status' => []])
                : null,
            'installed_at' => $row?->created_at?->toIso8601String(),
        ];
    }
}
