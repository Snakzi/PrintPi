<?php

namespace App\Http\Controllers;

use App\Http\Requests\FlashFirmwareRequest;
use App\Services\Firmware;
use App\Services\PrinterBridge;
use Carbon\CarbonImmutable;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Illuminate\Validation\ValidationException;
use Throwable;

class FirmwareController extends Controller
{
    public function __construct(
        private readonly Firmware $firmware,
        private readonly PrinterBridge $bridge,
    ) {}

    public function show(Request $request): JsonResponse
    {
        $overview = $this->firmware->overview($request->boolean('check'));
        if ($overview['checked_at'] !== null) {
            $overview['checked_at'] = CarbonImmutable::parse($overview['checked_at'])
                ->setTimezone(config('app.timezone'))->toIso8601String();
        }

        return response()->json($overview);
    }

    /**
     * Ask the daemon to list the printer's drive; the listing arrives with the next show().
     */
    public function files(): JsonResponse
    {
        abort_unless($this->bridge->isConnected(), 409, 'The printer is not connected.');
        abort_if($this->bridge->hasActiveJob(), 409, 'A print is running.');
        $this->bridge->listFirmwareFiles();

        return response()->json(['queued' => true], 202);
    }

    public function flash(FlashFirmwareRequest $request): JsonResponse
    {
        $method = $this->firmware->method();
        abort_if($method === null, 409, 'This printer cannot be updated from PrintPi.');
        abort_unless($this->bridge->isDaemonAlive(), 503, 'The daemon is not running.');
        abort_if($this->bridge->hasActiveJob(), 409, 'A print is running.');
        abort_if($this->bridge->isFlashingFirmware(), 409, 'A firmware update is already running.');

        $file = match ($method) {
            'buddy' => $this->driveFile($request),
            'avrdude' => $this->localFile($request),
            default => $this->nothing(),
        };
        $this->firmware->flash($method, $file);

        return response()->json(['status' => 'flashing', 'method' => $method, 'file' => $file === null ? null : basename($file)], 202);
    }

    private function driveFile(FlashFirmwareRequest $request): string
    {
        abort_unless($this->bridge->isConnected(), 409, 'The printer is not connected.');
        $name = $request->validated('name');
        if (! is_string($name) || $name === '') {
            throw ValidationException::withMessages(['name' => 'Choose a firmware file on the printer\'s USB drive.']);
        }
        if (! str_ends_with(strtolower($name), '.bbf')) {
            throw ValidationException::withMessages(['name' => 'Buddy firmware files end with .bbf.']);
        }
        if (! $this->firmware->isOnDrive($name)) {
            throw ValidationException::withMessages(['name' => 'This file is not on the printer\'s USB drive.']);
        }

        return $name;
    }

    private function localFile(FlashFirmwareRequest $request): string
    {
        if ($request->hasFile('file')) {
            return $this->firmware->store($request->file('file'));
        }
        if ($request->validated('source') !== 'release') {
            throw ValidationException::withMessages(['file' => 'Upload a firmware file.']);
        }
        $release = $this->firmware->latest()['release'];
        abort_if($release === null, 409, 'No firmware release is known for this printer.');
        try {
            return $this->firmware->download($release);
        } catch (Throwable $exception) {
            Log::warning('The firmware release could not be downloaded.', ['exception' => $exception]);
            abort(502, 'The firmware could not be downloaded.');
        }
    }

    private function nothing(): null
    {
        abort_unless($this->bridge->isConnected(), 409, 'The printer is not connected.');

        return null;
    }
}
