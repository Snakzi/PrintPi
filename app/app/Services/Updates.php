<?php

namespace App\Services;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use RuntimeException;
use Throwable;

class Updates
{
    public function __construct(
        private readonly Settings $settings,
        private readonly SystemControl $system,
    ) {}

    public function installedVersion(): string
    {
        $version = @file_get_contents(config('printpi.version_file'));

        return is_string($version) && trim($version) !== '' ? trim($version) : 'dev';
    }

    /**
     * The stored channel while the host publishes it, else the first published one, so
     * an install that chose a channel before it was dropped keeps getting updates.
     */
    public function channel(): string
    {
        $channels = config('printpi.update_channels');
        $stored = $this->settings->get('update_channel');

        return in_array($stored, $channels, true) ? $stored : $channels[0];
    }

    /**
     * The cached manifest of the current channel; `checked_at` is an ISO 8601 string
     * because the database cache store cannot hold objects.
     *
     * @return array{releases: list<array<string, mixed>>, checked_at: ?string, error: ?string}
     */
    public function manifest(bool $refresh = false): array
    {
        $channel = $this->channel();
        $key = 'printpi.updates.'.$channel;

        $cached = Cache::get($key);
        if (! $refresh && $cached !== null) {
            return $cached;
        }

        try {
            $manifest = Http::timeout(10)->acceptJson()
                ->get(rtrim(config('printpi.update_url'), '/').'/'.$channel.'/releases.json')
                ->throw()->object();

            if (! is_object($manifest) || ! is_array($manifest->releases ?? null)) {
                throw new RuntimeException('The update manifest does not contain a releases array.');
            }

            $releases = [];
            foreach ($manifest->releases as $release) {
                if (is_object($release) && is_string($release->version ?? null)) {
                    $releases[] = (array) $release;
                }
            }

            $result = ['releases' => $releases, 'checked_at' => CarbonImmutable::now()->toIso8601String(), 'error' => null];
        } catch (Throwable $exception) {
            Log::warning('The update manifest could not be fetched.', ['exception' => $exception]);

            $result = [
                'releases' => $cached['releases'] ?? [],
                'checked_at' => $cached['checked_at'] ?? null,
                'error' => 'The update server could not be reached.',
            ];
        }

        // A failed check is retried soon, a successful one holds for a day.
        Cache::put($key, $result, $result['error'] === null ? 86400 : 600);

        return $result;
    }

    /** @return array{version: string, date: mixed, notes: mixed, size: mixed, sha256: mixed, url: mixed}|null */
    public function available(): ?array
    {
        $installed = $this->installedVersion();
        $installed = $installed === 'dev' ? '0.0.0' : $installed;
        $available = null;

        foreach ($this->manifest()['releases'] as $release) {
            if (! version_compare($release['version'], $installed, '>')) {
                continue;
            }

            if (isset($release['min_version']) && (! is_string($release['min_version'])
                || version_compare($release['min_version'], $installed, '>'))) {
                continue;
            }

            if ($available === null || version_compare($release['version'], $available['version'], '>')) {
                $available = $release;
            }
        }

        if ($available === null) {
            return null;
        }

        return [
            'version' => $available['version'],
            'date' => $available['date'] ?? null,
            'notes' => $available['notes'] ?? null,
            'size' => $available['size'] ?? null,
            'sha256' => $available['sha256'] ?? null,
            'url' => $available['url'] ?? null,
        ];
    }

    /** @return array<string, mixed>|null */
    public function release(string $version): ?array
    {
        foreach ($this->manifest()['releases'] as $release) {
            if ($release['version'] === $version) {
                return $release;
            }
        }

        return null;
    }

    /** @return array<string, mixed>|null */
    public function status(): ?array
    {
        $contents = @file_get_contents(config('printpi.update_status_file'));
        if ($contents === false) {
            return null;
        }

        $status = json_decode($contents);

        return is_object($status) ? (array) $status : null;
    }

    public function inProgress(): bool
    {
        return in_array($this->status()['phase'] ?? null, [
            'queued', 'downloading', 'verifying', 'unpacking', 'installing', 'switching',
        ], true);
    }

    public function previousVersion(): ?string
    {
        $previous = rtrim(config('printpi.home'), '/').'/previous';
        if (! is_link($previous)) {
            return null;
        }

        $version = @file_get_contents($previous.'/VERSION');
        if (is_string($version) && trim($version) !== '') {
            return trim($version);
        }

        $target = readlink($previous);

        return $target !== false ? basename($target) : null;
    }

    public function start(string $version): bool
    {
        return $this->system->update($version, $this->channel());
    }

    public function rollback(): bool
    {
        return $this->system->rollback();
    }

    /**
     * Why the helper refused the last start or rollback, null when it accepted.
     */
    public function lastError(): ?string
    {
        return $this->system->lastError();
    }
}
