<?php

namespace App\Http\Controllers;

use App\Services\PrinterBridge;
use App\Services\SystemControl;
use Illuminate\Http\JsonResponse;

/**
 * Host actions from the user menu, refused with 503 on a machine without the
 * root helper such as a dev Mac, and the usage history the daemon samples.
 */
class SystemController extends Controller
{
    public function __construct(private readonly SystemControl $system, private readonly PrinterBridge $bridge) {}

    public function history(): JsonResponse
    {
        return response()->json($this->bridge->systemHistory());
    }

    public function reboot(): JsonResponse
    {
        $this->ensureAvailable();
        abort_unless($this->system->reboot(), 500, 'The reboot could not be started.');

        return response()->json(['status' => 'rebooting'], 202);
    }

    public function restartWebServer(): JsonResponse
    {
        $this->ensureAvailable();
        abort_unless($this->system->restartWebServer(), 500, 'The web server could not be restarted.');

        return response()->json(['status' => 'restarting'], 202);
    }

    private function ensureAvailable(): void
    {
        abort_unless($this->system->available(), 503, 'System control is not available on this host.');
    }
}
