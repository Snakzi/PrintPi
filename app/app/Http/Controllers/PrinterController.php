<?php

namespace App\Http\Controllers;

use App\Http\Requests\ConnectPrinterRequest;
use App\Http\Requests\SendGcodeRequest;
use App\Services\FilamentInventory;
use App\Services\PrinterBridge;
use App\Services\PrintHistory;
use App\Services\Settings;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class PrinterController extends Controller
{
    public function __construct(private readonly PrinterBridge $bridge) {}

    /**
     * The dashboard polls this, so ended prints are filed into the history on the way and
     * filament the walkthrough loaded is booked on its spool.
     */
    public function state(PrintHistory $history, FilamentInventory $inventory): JsonResponse
    {
        $history->sync();
        $inventory->sync();

        return response()->json($this->bridge->state());
    }

    public function serial(Request $request): JsonResponse
    {
        $limit = min(500, max(1, $request->integer('limit', 200)));

        return response()->json(['lines' => $this->bridge->serialLog($limit)]);
    }

    public function command(SendGcodeRequest $request): JsonResponse
    {
        $this->bridge->sendGcode($request->validated('command'));

        return $this->queued();
    }

    public function connect(ConnectPrinterRequest $request, Settings $settings): JsonResponse
    {
        $port = $request->validated('port');
        $baud = (int) $request->validated('baud');
        $settings->set(['serial_port' => $port, 'baud_rate' => $baud]);
        $this->bridge->connect($port, $baud);

        return $this->queued();
    }

    /** Reopens the port the last connect stored, so the UI can offer a one-click reconnect. */
    public function reconnect(Settings $settings): JsonResponse
    {
        $port = $settings->get('serial_port');
        abort_if(! $port, 409, 'No printer has been connected yet.');

        $this->bridge->connect($port, (int) $settings->get('baud_rate'));

        return $this->queued();
    }

    public function disconnect(): JsonResponse
    {
        $this->bridge->disconnect();

        return $this->queued();
    }

    public function emergencyStop(): JsonResponse
    {
        $this->bridge->emergencyStop();

        return $this->queued();
    }

    private function queued(): JsonResponse
    {
        return response()->json(['queued' => true], 202);
    }
}
