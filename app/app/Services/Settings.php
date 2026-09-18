<?php

namespace App\Services;

use App\Models\Setting;

/**
 * Key/value settings the UI can change, with defaults for anything not stored yet.
 */
class Settings
{
    /** @var array<string, mixed> */
    public const array DEFAULTS = [
        'serial_port' => null,
        'baud_rate' => 115200,
        'camera_device' => null,
        'camera_url' => null,
        'hostname' => null,
        'timezone' => null,
        // null follows the first of printpi.update_channels (Updates::channel).
        'update_channel' => null,
        'printer_profile' => null,
        'printer_name' => null,
        'energy_price' => null,
        'currency' => '€',
        // How the printer's firmware is flashed; null takes the profile's method (see Firmware).
        'firmware_method' => null,
        'firmware_mcu' => null,
        'firmware_programmer' => null,
        'firmware_baud' => null,
        'macros' => [
            ['label' => 'Home all', 'gcode' => 'G28'],
            ['label' => 'Preheat PLA', 'gcode' => "M104 S215\nM140 S60"],
            ['label' => 'Cool down', 'gcode' => "M104 S0\nM140 S0"],
            ['label' => 'Motors off', 'gcode' => 'M84'],
        ],
        // What happens around a print: the timelapse the daemon records and the files it makes from
        // it, the postcard the UI offers, the script the daemon runs after a cancel (empty for its
        // built-in one) and how many prints the history keeps (0 keeps them all).
        'timelapse' => true,
        'timelapse_gif' => true,
        'timelapse_mp4' => true,
        'postcard' => true,
        'cancel_gcode' => '',
        'history_keep' => 0,
        // What the browser shows: the toast when a print ends, plugin notifications, the job in the tab.
        'notify_print_end' => true,
        'notify_plugins' => true,
        'tab_progress' => true,
    ];

    /** @var list<int> */
    public const array BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 230400, 250000, 500000, 1000000];

    /**
     * @return array<string, mixed>
     */
    public function all(): array
    {
        $stored = Setting::query()
            ->whereIn('key', array_keys(self::DEFAULTS))
            ->get(['key', 'value'])
            ->pluck('value', 'key')
            ->all();

        return array_merge(self::DEFAULTS, $stored);
    }

    public function get(string $key): mixed
    {
        return $this->all()[$key] ?? null;
    }

    /**
     * @param  array<string, mixed>  $values
     * @return array<string, mixed>
     */
    public function set(array $values): array
    {
        foreach ($values as $key => $value) {
            if (! array_key_exists($key, self::DEFAULTS)) {
                continue;
            }
            Setting::query()->updateOrCreate(['key' => $key], ['value' => $value]);
        }

        return $this->all();
    }
}
