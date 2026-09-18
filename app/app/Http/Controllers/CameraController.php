<?php

namespace App\Http\Controllers;

use App\Services\PrinterBridge;
use App\Services\Settings;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class CameraController extends Controller
{
    public function __construct(
        private readonly PrinterBridge $bridge,
        private readonly Settings $settings,
    ) {}

    public function show(): JsonResponse
    {
        $webcam = rtrim((string) config('printpi.webcam_base'), '/');

        return response()->json([
            'cameras' => $this->bridge->cameras(),
            'status' => $this->bridge->camera(),
            'stream_url' => $webcam.'/stream',
            'snapshot_url' => $webcam.'/snapshot',
            'settings' => [
                'camera_device' => $this->settings->get('camera_device'),
                'camera_url' => $this->settings->get('camera_url'),
            ],
        ]);
    }

    public function start(Request $request): JsonResponse
    {
        $validated = $request->validate(['device' => ['nullable', 'string', 'max:200', 'regex:#^/dev/video\d+$#']]);
        $device = $validated['device'] ?? $this->settings->get('camera_device');
        if (! is_string($device) || $device === '') {
            return response()->json(['message' => 'No camera selected.'], 422);
        }
        $this->bridge->startCamera($device);

        return response()->json(['queued' => true, 'device' => $device], 202);
    }

    public function stop(): JsonResponse
    {
        $this->bridge->stopCamera();

        return response()->json(['queued' => true], 202);
    }
}
