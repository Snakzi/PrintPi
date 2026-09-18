<?php

namespace App\Http\Controllers;

use App\Http\Requests\FilamentAnswerRequest;
use App\Http\Requests\FilamentLoadRequest;
use App\Models\Spool;
use App\Services\FilamentChange;
use App\Services\PrinterBridge;
use Illuminate\Http\JsonResponse;

/**
 * The filament walkthrough: load, unload or change, then the answers the daemon waits for.
 * Its state travels with the printer state as `filament`.
 */
class FilamentChangeController extends Controller
{
    public function __construct(private readonly PrinterBridge $bridge, private readonly FilamentChange $change) {}

    public function load(FilamentLoadRequest $request): JsonResponse
    {
        $this->ensureFree();
        $id = $request->validated('spool_id');
        $spool = $id === null ? null : Spool::query()->findOrFail($id);
        $this->change->load($spool, $request->validated('material'), (bool) $request->validated('unload_first', false));

        return $this->queued();
    }

    public function unload(): JsonResponse
    {
        $this->ensureFree();
        $this->change->unload();

        return $this->queued();
    }

    public function proceed(): JsonResponse
    {
        $this->ensureRunning();
        $this->bridge->continueFilament();

        return $this->queued();
    }

    public function answer(FilamentAnswerRequest $request): JsonResponse
    {
        $this->ensureRunning();
        $this->bridge->answerFilament($request->validated('answer'));

        return $this->queued();
    }

    public function cancel(): JsonResponse
    {
        $this->ensureRunning();
        $this->bridge->cancelFilament();

        return $this->queued();
    }

    private function ensureFree(): void
    {
        abort_unless($this->bridge->isConnected(), 409, 'The printer is not connected.');
        abort_if($this->bridge->hasActiveJob(), 409, 'A print is running.');
        abort_if($this->bridge->hasActiveFilament(), 409, 'A filament change is already running.');
    }

    private function ensureRunning(): void
    {
        abort_unless($this->bridge->hasActiveFilament(), 409, 'No filament change is running.');
    }

    private function queued(): JsonResponse
    {
        return response()->json(['queued' => true], 202);
    }
}
