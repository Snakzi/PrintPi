<?php

namespace App\Services;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Throwable;

/**
 * The newest printer firmware Prusa published on GitHub for one printer family.
 *
 * Prusa keeps several release trains in one repository (the MK4 family, the XL, the
 * MINI and the CORE One take turns), so the releases are scanned for the asset that
 * names the family and the highest version wins, not the latest release.
 */
class FirmwareReleases
{
    /** @var array<string, string> */
    public const array REPOSITORIES = [
        'buddy' => 'prusa3d/Prusa-Firmware-Buddy',
        'prusa' => 'prusa3d/Prusa-Firmware',
    ];

    /** @var array<string, string> */
    private const array EXTENSIONS = ['buddy' => '.bbf', 'prusa' => '.hex'];

    private const int RELEASES_TO_SCAN = 40;

    public static function supports(string $firmware): bool
    {
        return isset(self::REPOSITORIES[$firmware]);
    }

    /**
     * Cached for a day, a failed fetch for ten minutes while the last result is kept.
     *
     * @return array{release: array{version: string, date: ?string, notes: ?string, name: string, size: ?int, url: string, page: ?string}|null, checked_at: ?string, error: ?string}
     */
    public function latest(string $firmware, string $family, bool $refresh = false): array
    {
        $key = 'printpi.firmware.'.$firmware.'.'.strtolower($family);
        $cached = Cache::get($key);
        if (! $refresh && $cached !== null) {
            return $cached;
        }

        try {
            $releases = Http::timeout(15)
                ->withHeaders(['Accept' => 'application/vnd.github+json', 'User-Agent' => 'PrintPi'])
                ->get('https://api.github.com/repos/'.self::REPOSITORIES[$firmware].'/releases', ['per_page' => self::RELEASES_TO_SCAN])
                ->throw()->json();

            $result = [
                'release' => $this->pick(is_array($releases) ? $releases : [], $family, self::EXTENSIONS[$firmware]),
                'checked_at' => CarbonImmutable::now()->toIso8601String(),
                'error' => null,
            ];
        } catch (Throwable $exception) {
            Log::warning('The printer firmware releases could not be fetched.', ['exception' => $exception]);

            $result = [
                'release' => $cached['release'] ?? null,
                'checked_at' => $cached['checked_at'] ?? null,
                'error' => 'GitHub could not be reached.',
            ];
        }

        Cache::put($key, $result, $result['error'] === null ? 86400 : 600);

        return $result;
    }

    /**
     * The highest stable release with an asset for the family.
     *
     * @param  list<mixed>  $releases
     * @return array{version: string, date: ?string, notes: ?string, name: string, size: ?int, url: string, page: ?string}|null
     */
    private function pick(array $releases, string $family, string $extension): ?array
    {
        $best = null;

        foreach ($releases as $release) {
            if (! is_array($release) || ($release['prerelease'] ?? false) || ($release['draft'] ?? false)) {
                continue;
            }
            $version = ltrim((string) ($release['tag_name'] ?? ''), 'v');
            if (! preg_match('/^\d+\.\d+(\.\d+)?$/', $version)) {
                continue;
            }
            $asset = $this->assetFor($release['assets'] ?? [], $family, $extension);
            if ($asset === null || ($best !== null && ! version_compare($version, $best['version'], '>'))) {
                continue;
            }

            $best = [
                'version' => $version,
                'date' => $release['published_at'] ?? null,
                'notes' => is_string($release['body'] ?? null) ? trim($release['body']) : null,
                'name' => $asset['name'],
                'size' => isset($asset['size']) ? (int) $asset['size'] : null,
                'url' => $asset['browser_download_url'],
                'page' => $release['html_url'] ?? null,
            ];
        }

        return $best;
    }

    /**
     * The asset whose name lists the family between underscores, e.g. MK4S in
     * MK4_MK4S_MK3.9_MK3.9S_firmware_6.5.7.bbf or MK3S in MK3S_MK3S+_FW_3.14.1_MULTILANG.hex.
     *
     * @return array{name: string, size?: int, browser_download_url: string}|null
     */
    private function assetFor(mixed $assets, string $family, string $extension): ?array
    {
        if (! is_array($assets)) {
            return null;
        }
        foreach ($assets as $asset) {
            $name = is_array($asset) ? ($asset['name'] ?? null) : null;
            if (! is_string($name) || ! is_string($asset['browser_download_url'] ?? null)
                || ! str_ends_with(strtolower($name), $extension)) {
                continue;
            }
            $tokens = array_map('strtoupper', explode('_', substr($name, 0, -strlen($extension))));
            if (in_array(strtoupper($family), $tokens, true)) {
                return $asset;
            }
        }

        return null;
    }
}
