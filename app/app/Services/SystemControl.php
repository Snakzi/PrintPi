<?php

namespace App\Services;

use Illuminate\Support\Facades\Process;

/**
 * The few system actions the web app may trigger, applied through a root
 * helper (deploy/bin/printpi-system) that sudoers allows for www-data.
 * Without the helper, on a dev machine, settings are stored but not applied
 * and reboot or restart are refused.
 */
class SystemControl
{
    private ?string $lastError = null;

    public function available(): bool
    {
        return is_executable($this->helper());
    }

    public function hostname(): string
    {
        $hostname = gethostname();

        return is_string($hostname) && $hostname !== '' ? strtolower(explode('.', $hostname)[0]) : 'printpi';
    }

    public function setHostname(string $hostname): bool
    {
        return $this->run('set-hostname', $hostname);
    }

    public function setTimezone(string $timezone): bool
    {
        return $this->run('set-timezone', $timezone);
    }

    /**
     * The helper schedules the reboot a moment later so this request still answers.
     */
    public function reboot(): bool
    {
        return $this->run('reboot');
    }

    /**
     * Restarts nginx and php-fpm, the two processes that serve this app.
     */
    public function restartWebServer(): bool
    {
        return $this->run('restart-web');
    }

    public function update(string $version, string $channel): bool
    {
        if (! preg_match('/^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$/', $version)
            || ! in_array($channel, ['stable', 'beta'], true)) {
            return false;
        }

        return $this->run('update', $version, $channel);
    }

    public function rollback(): bool
    {
        return $this->run('rollback');
    }

    /**
     * What the helper printed to stderr when the last action was refused, null after a success.
     */
    public function lastError(): ?string
    {
        return $this->lastError;
    }

    private function run(string $action, string ...$arguments): bool
    {
        if (! $this->available()) {
            return false;
        }

        $result = Process::timeout(20)->run(['sudo', '-n', $this->helper(), $action, ...$arguments]);
        $error = trim($result->errorOutput());
        $this->lastError = $result->successful() || $error === '' ? null : $error;

        return $result->successful();
    }

    private function helper(): string
    {
        return (string) config('printpi.system_helper');
    }
}
