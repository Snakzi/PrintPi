<?php

namespace App\Http\Controllers;

use App\Services\PrinterBridge;
use Illuminate\Http\JsonResponse;

/**
 * Controls the daemon's print job; starting one is files.print.
 */
class PrintJobController extends Controller
{
    public function __construct(private readonly PrinterBridge $bridge) {}

    public function pause(): JsonResponse
    {
        $this->bridge->pausePrint();

        return $this->queued();
    }

    public function resume(): JsonResponse
    {
        $this->bridge->resumePrint();

        return $this->queued();
    }

    public function cancel(): JsonResponse
    {
        $this->bridge->cancelPrint();

        return $this->queued();
    }

    public function restart(): JsonResponse
    {
        abort_unless($this->bridge->isConnected(), 409, 'The printer is not connected.');
        abort_if($this->bridge->hasActiveJob(), 409, 'A print is already running.');

        $this->bridge->restartPrint();

        return $this->queued();
    }

    private function queued(): JsonResponse
    {
        return response()->json(['queued' => true], 202);
    }
}
