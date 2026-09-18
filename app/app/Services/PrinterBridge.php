<?php

namespace App\Services;

use Illuminate\Redis\Connections\Connection;
use Illuminate\Support\Facades\Redis;

/**
 * Talks to the PrintPi daemon through Redis.
 *
 * The daemon keeps the latest printer state in a key, appends every serial line
 * to a capped list, refreshes a heartbeat key while it runs, and listens for
 * commands on a pub/sub channel. See daemon/printpi_daemon/bridge.py.
 */
class PrinterBridge
{
    public const string STATE_KEY = 'printpi:state';

    public const string HEARTBEAT_KEY = 'printpi:heartbeat';

    public const string PORTS_KEY = 'printpi:ports';

    public const string CAMERAS_KEY = 'printpi:cameras';

    public const string SYSTEM_KEY = 'printpi:system';

    public const string SYSTEM_HISTORY_KEY = 'printpi:system:history';

    /** Seconds between two points of the usage history, as the daemon writes them. */
    public const int SYSTEM_HISTORY_INTERVAL = 30;

    /** How far back the usage history reaches, in seconds. */
    public const int SYSTEM_HISTORY_SPAN = 86400;

    public const string CAMERA_KEY = 'printpi:camera';

    public const string SERIAL_LOG_KEY = 'printpi:serial:log';

    public const string PLUGINS_KEY = 'printpi:plugins';

    public const string PLUGIN_STATUS_KEY = 'printpi:plugins:status';

    public const string PLUGIN_STATE_KEY = 'printpi:plugins:state';

    public const string PLUGIN_REQUIREMENTS_KEY = 'printpi:plugins:requirements';

    public const string COMMAND_CHANNEL = 'printpi:commands';

    public const string JOBS_DONE_KEY = 'printpi:jobs:done';

    public const string NOTIFICATIONS_KEY = 'printpi:notifications';

    public const string FIRMWARE_KEY = 'printpi:firmware';

    public const string FIRMWARE_FILES_KEY = 'printpi:firmware:files';

    public const string FILAMENT_DONE_KEY = 'printpi:filament:done';

    /** Phases of a firmware update the daemon is still working on. */
    public const array ACTIVE_FIRMWARE_PHASES = ['preparing', 'flashing', 'rebooting', 'reconnecting'];

    /** Seconds without a heartbeat after which the daemon counts as down. */
    private const int HEARTBEAT_MAX_AGE = 10;

    /** Job states in which the daemon is still busy with the file. */
    private const array ACTIVE_JOB_STATES = ['printing', 'paused', 'cancelling'];

    /** Steps at which a filament walkthrough is over (see daemon/printpi_daemon/filament.py). */
    private const array ENDED_FILAMENT_STEPS = ['done', 'cancelled', 'error'];

    /**
     * @return array{daemon_alive: bool, printer: array<string, mixed>, ports: list<array{device: string, description: string, hwid: string}>, system: array<string, mixed>|null, power: array{plugin: string, id: string, name: string, on: bool, online: ?bool}|null, light: array{plugin: string, name: string, on: bool, color: ?string}|null, notifications: list<array<string, mixed>>}
     */
    public function state(): array
    {
        $statuses = $this->pluginStatuses();

        return [
            'daemon_alive' => $this->isDaemonAlive(),
            'printer' => $this->printer(),
            'ports' => $this->ports(),
            'system' => $this->system(),
            'power' => self::printerPowerFrom($statuses),
            'light' => self::printerLightFrom($statuses),
            'notifications' => $this->notifications(),
        ];
    }

    /**
     * The newest notifications plugins raised, oldest first; the UI toasts the ones it has not seen.
     *
     * @return list<array<string, mixed>>
     */
    public function notifications(int $limit = 20): array
    {
        $entries = $this->redis()->lrange(self::NOTIFICATIONS_KEY, -$limit, -1);
        $decoded = array_map(static fn (string $entry): mixed => json_decode($entry, true), $entries);

        return array_values(array_filter($decoded, static fn (mixed $entry): bool => is_array($entry) && isset($entry['id'], $entry['at'], $entry['message'])));
    }

    /**
     * The switch that powers the printer, when a running plugin reports one as printer_power in its status.
     *
     * @return array{plugin: string, id: string, name: string, on: bool, online: ?bool}|null
     */
    public function printerPower(): ?array
    {
        return self::printerPowerFrom($this->pluginStatuses());
    }

    /**
     * @param  array<string, array{state: string, status: array<string, mixed>}>  $statuses
     * @return array{plugin: string, id: string, name: string, on: bool, online: ?bool}|null
     */
    public static function printerPowerFrom(array $statuses): ?array
    {
        [$plugin, $power] = self::switchFrom($statuses, 'printer_power');

        if ($power === null || ! isset($power['id'])) {
            return null;
        }

        return [
            'plugin' => $plugin,
            'id' => (string) $power['id'],
            'name' => (string) ($power['name'] ?? ''),
            'on' => (bool) ($power['on'] ?? false),
            'online' => isset($power['online']) ? (bool) $power['online'] : null,
        ];
    }

    /**
     * The printer's light, when a running plugin reports one as printer_light in its status. A light
     * that reports its #rrggbb colour gets the picker under the status bar button, which sends
     * printer_light_color.
     *
     * @param  array<string, array{state: string, status: array<string, mixed>}>  $statuses
     * @return array{plugin: string, name: string, on: bool, color: ?string}|null
     */
    public static function printerLightFrom(array $statuses): ?array
    {
        [$plugin, $light] = self::switchFrom($statuses, 'printer_light');

        if ($light === null) {
            return null;
        }

        $color = $light['color'] ?? null;

        return [
            'plugin' => $plugin,
            'name' => (string) ($light['name'] ?? ''),
            'on' => (bool) ($light['on'] ?? false),
            'color' => is_string($color) && preg_match('/^#[0-9a-f]{6}$/i', $color) === 1 ? strtolower($color) : null,
        ];
    }

    /**
     * The first running plugin whose status carries $key as an object, with that object.
     *
     * @param  array<string, array{state: string, status: array<string, mixed>}>  $statuses
     * @return array{0: string, 1: array<string, mixed>|null}
     */
    private static function switchFrom(array $statuses, string $key): array
    {
        foreach ($statuses as $plugin => $entry) {
            $value = $entry['status'][$key] ?? null;

            if (($entry['state'] ?? null) === 'running' && is_array($value)) {
                return [(string) $plugin, $value];
            }
        }

        return ['', null];
    }

    /**
     * The daemon's latest printer state, or an offline placeholder.
     *
     * @return array<string, mixed>
     */
    public function printer(): array
    {
        $raw = $this->redis()->get(self::STATE_KEY);
        $printer = is_string($raw) ? json_decode($raw, true) : null;

        return is_array($printer) ? $printer : $this->offlineState();
    }

    public function isConnected(): bool
    {
        return ($this->printer()['connection'] ?? null) === 'connected';
    }

    /**
     * Whether a print is running, paused or still being cancelled.
     */
    public function hasActiveJob(): bool
    {
        return $this->activeJob() !== null;
    }

    /**
     * The daemon's job while it is running, paused or still being cancelled.
     *
     * @return array<string, mixed>|null
     */
    public function activeJob(): ?array
    {
        $job = $this->printer()['job'] ?? null;

        return is_array($job) && in_array($job['state'] ?? null, self::ACTIVE_JOB_STATES, true) ? $job : null;
    }

    /**
     * The filament walkthrough while the daemon is still on it: heating, waiting for the user, moving.
     *
     * @return array<string, mixed>|null
     */
    public function activeFilament(): ?array
    {
        $filament = $this->printer()['filament'] ?? null;

        return is_array($filament) && ! in_array($filament['step'] ?? null, self::ENDED_FILAMENT_STEPS, true) ? $filament : null;
    }

    public function hasActiveFilament(): bool
    {
        return $this->activeFilament() !== null;
    }

    /**
     * Serial ports the daemon currently sees, refreshed with its heartbeat.
     *
     * @return list<array{device: string, description: string, hwid: string}>
     */
    public function ports(): array
    {
        $raw = $this->redis()->get(self::PORTS_KEY);
        $ports = is_string($raw) ? json_decode($raw, true) : null;

        return is_array($ports) ? array_values($ports) : [];
    }

    public function isDaemonAlive(): bool
    {
        $stamp = $this->redis()->get(self::HEARTBEAT_KEY);

        return is_string($stamp) && (microtime(true) - (float) $stamp) < self::HEARTBEAT_MAX_AGE;
    }

    /**
     * @return list<array{dir: string, line: string, t: float}>
     */
    public function serialLog(int $limit = 200): array
    {
        $entries = $this->redis()->lrange(self::SERIAL_LOG_KEY, -$limit, -1);
        $decoded = array_map(static fn (string $entry): mixed => json_decode($entry, true), $entries);

        return array_values(array_filter($decoded, 'is_array'));
    }

    /**
     * USB cameras the daemon can see.
     *
     * @return list<array{device: string, name: string, bus: string, driver: string}>
     */
    public function cameras(): array
    {
        $raw = $this->redis()->get(self::CAMERAS_KEY);
        $cameras = is_string($raw) ? json_decode($raw, true) : null;

        return is_array($cameras) ? array_values($cameras) : [];
    }

    /**
     * @return array{running: bool, device: ?string, port: ?int, available: bool, error: ?string}
     */
    public function camera(): array
    {
        $raw = $this->redis()->get(self::CAMERA_KEY);
        $status = is_string($raw) ? json_decode($raw, true) : null;

        return array_merge(
            ['running' => false, 'device' => null, 'port' => null, 'available' => false, 'error' => null],
            is_array($status) ? $status : [],
        );
    }

    /**
     * Host statistics the daemon samples with its heartbeat.
     *
     * @return array<string, mixed>|null
     */
    public function system(): ?array
    {
        $raw = $this->redis()->get(self::SYSTEM_KEY);
        $stats = is_string($raw) ? json_decode($raw, true) : null;

        return is_array($stats) ? $stats : null;
    }

    /**
     * The CPU and memory usage of the last 24 hours, one point per interval.
     *
     * @return array{interval: int, points: list<array{0: int|float, 1: float|null, 2: float|null}>}
     */
    public function systemHistory(): array
    {
        $entries = $this->redis()->lrange(self::SYSTEM_HISTORY_KEY, 0, -1);

        return self::systemHistoryFrom(is_array($entries) ? $entries : [], microtime(true));
    }

    /**
     * Decodes the daemon's history entries and keeps the well-formed ones inside the span.
     *
     * @param  list<string>  $entries
     * @return array{interval: int, points: list<array{0: int|float, 1: float|null, 2: float|null}>}
     */
    public static function systemHistoryFrom(array $entries, float $now): array
    {
        $oldest = $now - self::SYSTEM_HISTORY_SPAN;
        $points = [];
        foreach ($entries as $entry) {
            $point = is_string($entry) ? json_decode($entry, true) : null;
            if (! is_array($point) || count($point) !== 3 || ! is_numeric($point[0]) || $point[0] < $oldest) {
                continue;
            }
            $points[] = [
                $point[0],
                is_numeric($point[1]) ? (float) $point[1] : null,
                is_numeric($point[2]) ? (float) $point[2] : null,
            ];
        }

        return ['interval' => self::SYSTEM_HISTORY_INTERVAL, 'points' => $points];
    }

    public function startCamera(string $device): void
    {
        $this->publish(['type' => 'camera_start', 'device' => $device]);
    }

    public function stopCamera(): void
    {
        $this->publish(['type' => 'camera_stop']);
    }

    /**
     * Hand the daemon the enabled plugins; it loads daemon/plugin.py from each path.
     *
     * @param  list<array{id: string, path: string, version: string, settings: array<string, mixed>}>  $plugins
     */
    public function syncPlugins(array $plugins): void
    {
        $this->redis()->set(self::PLUGINS_KEY, json_encode(array_values($plugins), JSON_THROW_ON_ERROR));
        $this->publish(['type' => 'plugins_sync']);
    }

    /**
     * State of every plugin the daemon has loaded, keyed by plugin id.
     *
     * @return array<string, array{state: string, error: ?string, version: ?string, status: array<string, mixed>}>
     */
    public function pluginStatuses(): array
    {
        $raw = $this->redis()->get(self::PLUGIN_STATUS_KEY);
        $statuses = is_string($raw) ? json_decode($raw, true) : null;

        return is_array($statuses) ? array_filter($statuses, 'is_array') : [];
    }

    public function pluginAction(string $id, string $action, mixed $value): void
    {
        $this->publish(['type' => 'plugin_action', 'id' => $id, 'action' => $action, 'value' => $value]);
    }

    /**
     * Drop what the daemon remembered about a plugin, so a reinstall starts clean.
     */
    public function forgetPlugin(string $id): void
    {
        $this->redis()->hdel(self::PLUGIN_STATE_KEY, [$id]);
        $this->redis()->hdel(self::PLUGIN_REQUIREMENTS_KEY, [$id]);
    }

    public function sendGcode(string $command): void
    {
        $this->publish(['type' => 'gcode', 'command' => $command]);
    }

    public function connect(?string $port = null, ?int $baud = null): void
    {
        $this->publish(array_filter(['type' => 'connect', 'port' => $port, 'baud' => $baud]));
    }

    public function disconnect(): void
    {
        $this->publish(['type' => 'disconnect']);
    }

    public function emergencyStop(): void
    {
        $this->publish(['type' => 'emergency_stop']);
    }

    /**
     * Stream a G-code file the daemon can read from disk; the estimate feeds the remaining
     * time and the camera URL the timelapse when the daemon runs no stream of its own.
     */
    /**
     * @param  array{x: int|float, y: int|float, z?: int|float, centered: bool}|null  $bed  where a pause may park the head on non-Prusa firmware
     */
    /**
     * @param  array{enabled: bool, gif: bool, mp4: bool}|null  $timelapse  what to record; null records everything
     * @param  list<string>|null  $cancelGcode  the script after a cancel; null for the daemon's own
     */
    public function startPrint(string $path, string $name, ?int $fileId = null, ?int $estimatedSeconds = null, ?string $cameraUrl = null, ?array $bed = null, ?array $timelapse = null, ?array $cancelGcode = null): void
    {
        $this->publish([
            'type' => 'print_start',
            'path' => $path,
            'name' => $name,
            'file_id' => $fileId,
            'estimated_seconds' => $estimatedSeconds,
            'camera_url' => $cameraUrl,
            'bed' => $bed,
            'timelapse' => $timelapse,
            'cancel_gcode' => $cancelGcode,
        ]);
    }

    /**
     * The records of ended print jobs the daemon left behind, oldest first; they are taken off Redis.
     *
     * @return list<array<string, mixed>>
     */
    public function takeFinishedJobs(): array
    {
        $redis = $this->redis();
        $entries = $redis->lrange(self::JOBS_DONE_KEY, 0, -1);
        if (! is_array($entries) || $entries === []) {
            return [];
        }
        $redis->ltrim(self::JOBS_DONE_KEY, count($entries), -1);
        $decoded = array_map(static fn (string $entry): mixed => json_decode($entry, true), $entries);

        return array_values(array_filter($decoded, 'is_array'));
    }

    /**
     * Starts the daemon's filament walkthrough (see daemon/printpi_daemon/filament.py).
     *
     * @param  'load'|'unload'|'change'  $action
     * @param  array{id: int, name: string, material: ?string, color: ?string}|null  $spool  the spool going in, for the record
     * @param  array{load: list<array{float, float}>, purge: array{float, float}, unload: list<array{float, float}>}|null  $moves  the profile's moves
     */
    public function startFilament(string $action, ?array $spool, ?string $material, ?int $nozzle, ?int $unloadNozzle, ?array $moves): void
    {
        $this->publish([
            'type' => 'filament_start',
            'action' => $action,
            'spool' => $spool,
            'material' => $material,
            'nozzle' => $nozzle,
            'unload_nozzle' => $unloadNozzle,
            'moves' => $moves,
        ]);
    }

    /** The user inserted or pulled out the filament. */
    public function continueFilament(): void
    {
        $this->publish(['type' => 'filament_continue']);
    }

    /**
     * @param  'yes'|'purge'  $answer  to the colour check
     */
    public function answerFilament(string $answer): void
    {
        $this->publish(['type' => 'filament_answer', 'answer' => $answer]);
    }

    public function cancelFilament(): void
    {
        $this->publish(['type' => 'filament_cancel']);
    }

    /**
     * What the walkthrough put in or took out since the last call, oldest first; taken off Redis.
     *
     * @return list<array{event: string, spool: array<string, mixed>|null, at: float}>
     */
    public function takeFilamentEvents(): array
    {
        $redis = $this->redis();
        $entries = $redis->lrange(self::FILAMENT_DONE_KEY, 0, -1);
        if (! is_array($entries) || $entries === []) {
            return [];
        }
        $redis->ltrim(self::FILAMENT_DONE_KEY, count($entries), -1);
        $decoded = array_map(static fn (string $entry): mixed => json_decode($entry, true), $entries);

        return array_values(array_filter($decoded, static fn (mixed $entry): bool => is_array($entry) && isset($entry['event'])));
    }

    public function pausePrint(): void
    {
        $this->publish(['type' => 'print_pause']);
    }

    public function resumePrint(): void
    {
        $this->publish(['type' => 'print_resume']);
    }

    public function cancelPrint(): void
    {
        $this->publish(['type' => 'print_cancel']);
    }

    /**
     * Print the daemon's last job again.
     */
    public function restartPrint(): void
    {
        $this->publish(['type' => 'print_restart']);
    }

    /**
     * State of the printer firmware update the daemon runs or last ran (see daemon/printpi_daemon/firmware.py).
     *
     * @return array<string, mixed>
     */
    public function firmwareStatus(): array
    {
        $raw = $this->redis()->get(self::FIRMWARE_KEY);
        $status = is_string($raw) ? json_decode($raw, true) : null;

        return array_merge([
            'phase' => 'idle', 'method' => null, 'file' => null, 'step' => null, 'progress' => null, 'log' => [],
            'error' => null, 'started_at' => null, 'finished_at' => null, 'firmware_before' => null,
            'firmware_after' => null, 'avrdude_available' => false,
        ], is_array($status) ? $status : []);
    }

    public function isFlashingFirmware(): bool
    {
        return in_array($this->firmwareStatus()['phase'], self::ACTIVE_FIRMWARE_PHASES, true);
    }

    /**
     * The last listing of the printer's SD card or USB drive the daemon took.
     *
     * @return array{files: list<array{name: string, size: ?int, long_name: ?string}>, listed_at: ?float, error: ?string}
     */
    public function firmwareFiles(): array
    {
        $raw = $this->redis()->get(self::FIRMWARE_FILES_KEY);
        $listing = is_string($raw) ? json_decode($raw, true) : null;
        $listing = is_array($listing) ? $listing : [];

        return [
            'files' => array_values(array_filter($listing['files'] ?? [], 'is_array')),
            'listed_at' => $listing['listed_at'] ?? null,
            'error' => $listing['error'] ?? null,
        ];
    }

    /**
     * Ask the daemon for a fresh listing of the printer's drive.
     */
    public function listFirmwareFiles(): void
    {
        $this->publish(['type' => 'firmware_files']);
    }

    /**
     * Start a firmware update; file is a name on the printer's drive for buddy and a path on this host for avrdude.
     *
     * @param  array{method: string, file?: ?string, mcu?: ?string, programmer?: ?string, baud?: ?int}  $options
     */
    public function flashFirmware(array $options): void
    {
        $this->publish(['type' => 'firmware_flash'] + $options);
    }

    /**
     * @param  array<string, mixed>  $command
     */
    private function publish(array $command): void
    {
        $this->redis()->publish(self::COMMAND_CHANNEL, json_encode($command, JSON_THROW_ON_ERROR));
    }

    private function redis(): Connection
    {
        return Redis::connection('printpi');
    }

    /**
     * @return array<string, mixed>
     */
    private function offlineState(): array
    {
        return [
            'port' => null,
            'baudrate' => null,
            'connection' => 'offline',
            'status' => 'idle',
            'firmware' => [],
            'capabilities' => [],
            'temperatures' => [],
            'position' => [],
            'last_error' => null,
            'updated_at' => null,
            'job' => null,
            'filament' => null,
        ];
    }
}
