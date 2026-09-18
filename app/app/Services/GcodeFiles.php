<?php

namespace App\Services;

use App\Models\GcodeFile;
use Illuminate\Contracts\Filesystem\Filesystem;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;

/**
 * The G-code library on the gcode disk: one GcodeFile row per name, same name replaces.
 * Both the dashboard upload and the slicer upload endpoint go through here.
 */
class GcodeFiles
{
    public const string DISK = 'gcode';

    public function __construct(
        private readonly GcodeMetadata $metadata,
        private readonly GcodeThumbnail $thumbnails,
        private readonly PrinterBridge $bridge,
        private readonly Settings $settings,
        private readonly PrinterCatalog $catalog,
    ) {}

    public function disk(): Filesystem
    {
        return Storage::disk(self::DISK);
    }

    public function store(UploadedFile $upload): GcodeFile
    {
        $name = $this->safeName($upload->getClientOriginalName());
        $disk = $this->disk();
        $disk->putFileAs('', $upload, $name);

        $file = GcodeFile::query()->updateOrCreate(
            ['name' => $name],
            ['size' => $disk->size($name), 'metadata' => $this->metadata->fromPath($disk->path($name))],
        );
        $file->fill(['thumbnail' => $this->replaceThumbnail($file, $disk->path($name))])->touch();

        return $file;
    }

    public function delete(GcodeFile $file): void
    {
        $disk = $this->disk();
        $disk->delete($file->name);
        if ($file->thumbnail !== null) {
            $disk->delete($file->thumbnail);
        }
        $file->delete();
    }

    /**
     * The daemon reads the file straight from the gcode disk, so it gets the absolute path.
     * A stream URL goes along for the timelapse when the camera is not one the daemon runs itself,
     * and the profile's bed so a pause can park the head out of the way.
     */
    public function print(GcodeFile $file): void
    {
        $cameraUrl = $this->settings->get('camera_device') ? null : $this->settings->get('camera_url');
        $this->bridge->startPrint(
            $this->disk()->path($file->name),
            $file->name,
            $file->id,
            $file->metadata['estimated_seconds'] ?? null,
            is_string($cameraUrl) && $cameraUrl !== '' ? $cameraUrl : null,
            $this->bed(),
            [
                'enabled' => (bool) $this->settings->get('timelapse'),
                'gif' => (bool) $this->settings->get('timelapse_gif'),
                'mp4' => (bool) $this->settings->get('timelapse_mp4'),
            ],
            $this->cancelGcode(),
        );
    }

    /**
     * The cancel script from the settings as lines, or null so the daemon runs its own.
     *
     * @return list<string>|null
     */
    private function cancelGcode(): ?array
    {
        $script = $this->settings->get('cancel_gcode');
        $lines = is_string($script) ? array_values(array_filter(array_map('trim', preg_split('/\R/', $script)), 'strlen')) : [];

        return $lines === [] ? null : $lines;
    }

    /**
     * The configured printer's bed as the daemon wants it; a delta's bed is centred on the origin.
     *
     * @return array{x: int|float, y: int|float, z?: int|float, centered: bool}|null
     */
    private function bed(): ?array
    {
        $id = $this->settings->get('printer_profile');
        $profile = is_string($id) ? $this->catalog->find($id) : null;
        if (! is_array($profile) || ! is_array($profile['bed'] ?? null)) {
            return null;
        }

        return [...$profile['bed'], 'centered' => ($profile['type'] ?? null) === 'delta'];
    }

    /**
     * Whether the running job streams this name; the daemon reads it line by line from disk,
     * so replacing it would corrupt the print.
     */
    public function isBeingPrinted(string $name): bool
    {
        $job = $this->bridge->activeJob();

        return $job !== null && ($job['path'] ?? null) === $this->disk()->path($name);
    }

    /**
     * Keep only the base name and characters that are safe on every filesystem.
     */
    public function safeName(string $original): string
    {
        $base = basename(str_replace('\\', '/', $original));
        $clean = trim((string) preg_replace('/[^A-Za-z0-9._ ()-]+/', '_', $base), '. ');

        return $clean !== '' ? $clean : 'upload.gcode';
    }

    /**
     * Stores the image embedded in the upload under thumbnails/<id>.<ext> and
     * drops the previous one; returns the new disk path or null.
     */
    private function replaceThumbnail(GcodeFile $file, string $gcodePath): ?string
    {
        $disk = $this->disk();
        if ($file->thumbnail !== null) {
            $disk->delete($file->thumbnail);
        }

        $image = $this->thumbnails->fromPath($gcodePath);
        if ($image === null) {
            return null;
        }

        $path = "thumbnails/{$file->id}.{$image['extension']}";
        $disk->put($path, $image['data']);

        return $path;
    }
}
