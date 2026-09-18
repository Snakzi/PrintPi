<?php

namespace App\Services;

use App\Models\GcodeFile;
use App\Models\PrintJob;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Storage;

/**
 * The print history: every job the daemon finished, cancelled or lost, filed from
 * the records it leaves in Redis. Metadata and thumbnail are copied from the
 * G-code file at that moment so a postcard survives the file's deletion; the
 * timelapse stays where the daemon wrote it, below the shared timelapse directory.
 * The filament a print used is booked on the spool loaded at that moment.
 */
class PrintHistory
{
    public const string DISK = 'gcode';

    private const array FINAL_STATES = ['finished', 'cancelled', 'error'];

    public function __construct(
        private readonly PrinterBridge $bridge,
        private readonly Settings $settings,
        private readonly PrinterCatalog $printers,
        private readonly FilamentInventory $inventory,
    ) {}

    /**
     * Drain the daemon's records into the table.
     *
     * @return list<PrintJob> the jobs filed by this call
     */
    public function sync(): array
    {
        $filed = [];
        foreach ($this->bridge->takeFinishedJobs() as $record) {
            $job = $this->file($record);
            if ($job !== null) {
                $filed[] = $job;
            }
        }
        if ($filed !== []) {
            $this->prune();
        }

        return $filed;
    }

    /**
     * Drop the oldest prints beyond the history_keep setting, with their files; 0 keeps everything.
     */
    public function prune(): void
    {
        $keep = (int) $this->settings->get('history_keep');
        if ($keep <= 0) {
            return;
        }
        PrintJob::query()->orderByDesc('id')->skip($keep)->take(PHP_INT_MAX)->get()->each(fn (PrintJob $job) => $this->delete($job));
    }

    /**
     * File one record of the daemon; a record seen before is ignored.
     *
     * @param  array<string, mixed>  $record
     */
    public function file(array $record): ?PrintJob
    {
        $key = (string) ($record['id'] ?? '');
        if ($key === '' || PrintJob::query()->where('key', $key)->exists()) {
            return null;
        }

        $file = isset($record['file_id']) ? GcodeFile::query()->find((int) $record['file_id']) : null;
        $timelapse = is_array($record['timelapse'] ?? null) ? $record['timelapse'] : [];
        $progress = max(0.0, min(1.0, (float) ($record['progress'] ?? 0)));
        $state = (string) ($record['state'] ?? 'error');
        $spool = $this->inventory->loaded();
        $millimetres = self::scaled($file?->metadata['filament_mm'] ?? null, $progress);
        $grams = self::scaled($file?->metadata['filament_g'] ?? null, $progress);
        // A slicer that reports only the length leaves the weight to the spool's density.
        if ($grams === null && $millimetres !== null && $spool !== null) {
            $grams = $spool->gramsFor($millimetres);
        }

        $job = PrintJob::query()->create([
            'key' => $key,
            'gcode_file_id' => $file?->id,
            'name' => (string) ($record['name'] ?? 'print'),
            'state' => in_array($state, self::FINAL_STATES, true) ? $state : 'error',
            'error' => isset($record['error']) ? (string) $record['error'] : null,
            'started_at' => self::moment((float) ($record['started_at'] ?? microtime(true))),
            'finished_at' => isset($record['finished_at']) ? self::moment((float) $record['finished_at']) : null,
            'elapsed' => (int) round((float) ($record['elapsed'] ?? 0)),
            'progress' => $progress,
            'layers' => (int) ($record['layer'] ?? 0),
            'total_layers' => isset($record['total_layers']) ? (int) $record['total_layers'] : null,
            'filament_g' => $grams,
            'filament_mm' => $millimetres,
            'slicer' => $file?->metadata['slicer'] ?? null,
            'printer' => $this->printerName(),
            'thumbnail' => $this->copyThumbnail($file, $key),
            'cover' => $this->relativeTimelapsePath($timelapse['cover'] ?? null),
            'timelapse' => $this->relativeTimelapsePath($timelapse['gif'] ?? null),
            'video' => $this->relativeTimelapsePath($timelapse['mp4'] ?? null),
            'frames' => (int) ($timelapse['frames'] ?? 0),
            'energy_wh' => isset($record['energy_wh']) ? (float) $record['energy_wh'] : null,
        ]);
        $this->inventory->assign($job, $spool);

        return $job;
    }

    public function delete(PrintJob $job): void
    {
        if ($job->thumbnail !== null) {
            Storage::disk(self::DISK)->delete($job->thumbnail);
        }
        $directory = $this->timelapsePath($job->key);
        if ($directory !== null && is_dir($directory)) {
            File::deleteDirectory($directory);
        }
        $job->delete();
    }

    /**
     * The absolute path of a timelapse file of a job, or null when it is gone.
     */
    public function timelapseFile(?string $relative): ?string
    {
        if ($relative === null) {
            return null;
        }
        $path = $this->timelapsePath($relative);

        return $path !== null && is_file($path) ? $path : null;
    }

    private function timelapsePath(string $relative): ?string
    {
        if ($relative === '' || str_contains($relative, '..')) {
            return null;
        }

        return rtrim((string) config('printpi.timelapse_dir'), '/').'/'.ltrim($relative, '/');
    }

    /**
     * The daemon reports absolute paths; only files below the timelapse directory are kept, relative to it.
     */
    private function relativeTimelapsePath(mixed $absolute): ?string
    {
        if (! is_string($absolute) || $absolute === '') {
            return null;
        }
        $root = realpath((string) config('printpi.timelapse_dir'));
        $real = realpath($absolute);
        if ($root === false || $real === false || ! str_starts_with($real, $root.DIRECTORY_SEPARATOR)) {
            return null;
        }

        return substr($real, strlen($root) + 1);
    }

    /**
     * A copy of the file's thumbnail under postcards/, so the history keeps its picture.
     */
    private function copyThumbnail(?GcodeFile $file, string $key): ?string
    {
        if ($file?->thumbnail === null) {
            return null;
        }
        $disk = Storage::disk(self::DISK);
        $target = 'postcards/'.$key.'.'.pathinfo($file->thumbnail, PATHINFO_EXTENSION);

        return $disk->exists($file->thumbnail) && $disk->copy($file->thumbnail, $target) ? $target : null;
    }

    private function printerName(): ?string
    {
        $name = $this->settings->get('printer_name');
        if (is_string($name) && $name !== '') {
            return $name;
        }
        $profile = $this->settings->get('printer_profile');

        return is_string($profile) ? ($this->printers->find($profile)['model'] ?? null) : null;
    }

    /**
     * A Unix timestamp of the daemon in the app's timezone; Carbon would otherwise assume UTC.
     */
    private static function moment(float $timestamp): Carbon
    {
        return Carbon::createFromTimestamp($timestamp, config('app.timezone'));
    }

    /**
     * The file's total scaled to how much of it was printed.
     */
    private static function scaled(mixed $total, float $progress): ?float
    {
        return is_numeric($total) ? round((float) $total * $progress, 2) : null;
    }
}
