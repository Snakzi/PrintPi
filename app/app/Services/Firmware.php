<?php

namespace App\Services;

use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;

/**
 * Printer firmware updates: what the printer runs, what Prusa published and how
 * this printer is flashed. The flash itself runs in the daemon (firmware.py).
 *
 * The method follows the profile's firmware type: Buddy boards flash a .bbf from
 * their USB drive, the Prusa MK3 family is written with avrdude over the serial
 * port, other Marlin boards are restarted to pick up firmware.bin from the SD card.
 * The firmware_method setting overrides that, e.g. avrdude for an 8-bit board with a bootloader.
 */
class Firmware
{
    /** @var list<string> */
    public const array METHODS = ['buddy', 'avrdude', 'restart'];

    /** Directory on the gcode disk that holds uploaded and downloaded firmware files. */
    public const string DIRECTORY = 'firmware';

    /** @var array<string, string> */
    private const array DEFAULT_METHODS = ['buddy' => 'buddy', 'prusa' => 'avrdude', 'marlin' => 'restart'];

    public function __construct(
        private readonly Settings $settings,
        private readonly PrinterCatalog $catalog,
        private readonly PrinterBridge $bridge,
        private readonly FirmwareReleases $releases,
    ) {}

    /**
     * @return array<string, mixed>|null
     */
    public function profile(): ?array
    {
        $id = $this->settings->get('printer_profile');

        return is_string($id) ? $this->catalog->find($id) : null;
    }

    /**
     * The flash method for the configured printer, null when it cannot be flashed from here.
     */
    public function method(): ?string
    {
        $default = self::DEFAULT_METHODS[$this->profile()['firmware'] ?? ''] ?? null;
        if ($default === null) {
            return null;
        }
        $chosen = $this->settings->get('firmware_method');

        return in_array($chosen, self::METHODS, true) ? $chosen : $default;
    }

    /**
     * The avrdude parameters: the settings, else what the profile's board needs.
     *
     * @return array{mcu: string, programmer: string, baud: int}
     */
    public function avrdude(): array
    {
        [$mcu, $programmer] = ($this->profile()['firmware'] ?? null) === 'prusa'
            ? ['atmega2560', 'wiring']
            : ['atmega1284p', 'arduino'];
        $values = $this->settings->all();

        return [
            'mcu' => is_string($values['firmware_mcu']) && $values['firmware_mcu'] !== '' ? $values['firmware_mcu'] : $mcu,
            'programmer' => is_string($values['firmware_programmer']) && $values['firmware_programmer'] !== '' ? $values['firmware_programmer'] : $programmer,
            'baud' => (int) ($values['firmware_baud'] ?: 115200),
        ];
    }

    /**
     * The firmware the connected printer reported with M115.
     *
     * @return array{name: ?string, version: ?string}
     */
    public function installed(): array
    {
        $name = $this->bridge->printer()['firmware']['FIRMWARE_NAME'] ?? null;
        $name = is_string($name) && $name !== '' ? $name : null;

        return ['name' => $name, 'version' => self::versionOf($name)];
    }

    /**
     * "Prusa-Firmware-Buddy 6.4.0+14924 (Github)" gives 6.4.0, "Marlin 2.1.2.4 (Sep 15 2026)" 2.1.2.4.
     */
    public static function versionOf(?string $name): ?string
    {
        if ($name === null || ! preg_match('/(?<![\d.])(\d+(?:\.\d+){1,3})(?![\d.])/', $name, $match)) {
            return null;
        }

        return $match[1];
    }

    /**
     * The newest release Prusa published for this printer's family.
     *
     * @return array{release: array<string, mixed>|null, checked_at: ?string, error: ?string}
     */
    public function latest(bool $refresh = false): array
    {
        $profile = $this->profile();
        $family = $profile['firmware_family'] ?? null;
        if (! is_string($family) || ! FirmwareReleases::supports($profile['firmware'])) {
            return ['release' => null, 'checked_at' => null, 'error' => null];
        }

        return $this->releases->latest($profile['firmware'], $family, $refresh);
    }

    /**
     * Everything the firmware card shows.
     *
     * @return array<string, mixed>
     */
    public function overview(bool $refresh = false): array
    {
        $profile = $this->profile();
        $installed = $this->installed();
        $latest = $this->latest($refresh);
        $release = $latest['release'];
        $method = $this->method();

        return [
            'profile' => $profile === null ? null : [
                'id' => $profile['id'],
                'model' => $profile['model'],
                'firmware' => $profile['firmware'],
                'family' => $profile['firmware_family'],
            ],
            'method' => $method,
            'methods' => $method === null ? [] : self::METHODS,
            'connected' => $this->bridge->isConnected(),
            'installed' => $installed,
            'latest' => $release,
            'up_to_date' => $release !== null && $installed['version'] !== null
                ? ! version_compare($release['version'], $installed['version'], '>')
                : null,
            'checked_at' => $latest['checked_at'],
            'error' => $latest['error'],
            'avrdude' => $this->avrdude(),
            'status' => $this->bridge->firmwareStatus(),
            'files' => $this->bridge->firmwareFiles(),
        ];
    }

    /**
     * Whether the daemon's last drive listing holds this file.
     */
    public function isOnDrive(string $name): bool
    {
        foreach ($this->bridge->firmwareFiles()['files'] as $file) {
            if (($file['name'] ?? null) === $name) {
                return true;
            }
        }

        return false;
    }

    /**
     * Keep an uploaded firmware file where the daemon can read it; returns its absolute path.
     */
    public function store(UploadedFile $file): string
    {
        $name = preg_replace('/[^A-Za-z0-9._+-]+/', '_', $file->getClientOriginalName());
        $name = is_string($name) && $name !== '' && $name !== '.' ? $name : 'firmware.hex';
        $disk = Storage::disk('gcode');
        $disk->putFileAs(self::DIRECTORY, $file, $name);

        return $disk->path(self::DIRECTORY.'/'.$name);
    }

    /**
     * Fetch a release's firmware file for the flash tool; returns its absolute path.
     *
     * @param  array{name: string, url: string}  $release
     */
    public function download(array $release): string
    {
        $name = basename($release['name']);
        $disk = Storage::disk('gcode');
        $disk->put(self::DIRECTORY.'/'.$name, Http::timeout(120)->get($release['url'])->throw()->body());

        return $disk->path(self::DIRECTORY.'/'.$name);
    }

    /**
     * Hand the flash to the daemon; $file is a name on the printer's drive for buddy and a path here for avrdude.
     */
    public function flash(string $method, ?string $file = null): void
    {
        $command = ['method' => $method, 'file' => $file];
        if ($method === 'avrdude') {
            $command += $this->avrdude();
        }
        $this->bridge->flashFirmware($command);
    }
}
