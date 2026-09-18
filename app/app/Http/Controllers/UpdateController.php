<?php

namespace App\Http\Controllers;

use App\Http\Requests\StartUpdateRequest;
use App\Services\PrinterBridge;
use App\Services\SystemControl;
use App\Services\Updates;
use Carbon\CarbonImmutable;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;

class UpdateController extends Controller
{
    public function __construct(
        private readonly Updates $updates,
        private readonly SystemControl $system,
        private readonly PrinterBridge $bridge,
    ) {}

    public function show(Request $request): JsonResponse
    {
        $manifest = $this->updates->manifest($request->boolean('check'));

        return response()->json([
            'installed' => $this->updates->installedVersion(),
            'channel' => $this->updates->channel(),
            'channels' => config('printpi.update_channels'),
            'update_url' => config('printpi.update_url'),
            'available' => $this->updates->available(),
            'checked_at' => $manifest['checked_at'] === null ? null : CarbonImmutable::parse($manifest['checked_at'])->setTimezone(config('app.timezone'))->toIso8601String(),
            'error' => $manifest['error'],
            'status' => $this->updates->status(),
            'previous' => $this->updates->previousVersion(),
            'system_control' => $this->system->available(),
        ]);
    }

    public function start(StartUpdateRequest $request): JsonResponse
    {
        $this->ensureReady();
        $version = $request->validated('version');

        if ($this->updates->release($version) === null) {
            throw ValidationException::withMessages(['version' => 'This version is not available.']);
        }

        abort_unless($this->updates->start($version), 500, $this->refusal('The update could not be started.'));

        return response()->json(['status' => 'updating', 'version' => $version], 202);
    }

    public function rollback(): JsonResponse
    {
        $this->ensureReady();
        $version = $this->updates->previousVersion();
        abort_if($version === null, 409, 'Nothing to roll back to.');
        abort_unless($this->updates->rollback(), 500, $this->refusal('The rollback could not be started.'));

        return response()->json(['status' => 'rolling_back', 'version' => $version], 202);
    }

    /**
     * The helper's reason as a sentence, else the fallback.
     */
    private function refusal(string $fallback): string
    {
        $reason = $this->updates->lastError();

        return $reason === null ? $fallback : Str::ucfirst(rtrim($reason, '.')).'.';
    }

    private function ensureReady(): void
    {
        abort_unless($this->system->available(), 503, 'System control is not available on this host.');
        abort_if($this->updates->inProgress(), 409, 'An update is already running.');
        abort_if($this->bridge->hasActiveJob(), 409, 'A print is running.');
    }
}
