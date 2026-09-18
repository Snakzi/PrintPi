<?php

namespace App\Http\Controllers;

use App\Http\Requests\PrintHostUploadRequest;
use App\Services\GcodeFiles;
use App\Services\PrinterBridge;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Response;

/**
 * The two print host endpoints slicers use to send a file: PrusaSlicer, OrcaSlicer, SuperSlicer
 * and Cura test the host with GET api/version and upload to POST api/files/local.
 * Errors are plain sentences because the slicers show the response body to the user.
 */
class PrintHostController extends Controller
{
    public function __construct(private readonly GcodeFiles $files, private readonly PrinterBridge $bridge) {}

    /**
     * PrusaSlicer and OrcaSlicer only require `api`; a `text` field would have to name a
     * host type they know, so none is sent. Cura reads `server`.
     */
    public function version(): JsonResponse
    {
        return response()->json([
            'api' => '0.1',
            'server' => '1.5.0',
        ]);
    }

    /**
     * The file is stored even when the requested print cannot start, so a slicer's
     * "Upload and Print" against an idle printer leaves the file ready in the library.
     */
    public function upload(PrintHostUploadRequest $request): JsonResponse|Response
    {
        $upload = $request->file('file');
        $name = $this->files->safeName($upload->getClientOriginalName());
        if ($this->files->isBeingPrinted($name)) {
            return $this->refuse("$name is being printed right now.");
        }

        $file = $this->files->store($upload);

        if ($request->boolean('print')) {
            if (! $this->bridge->isConnected()) {
                return $this->refuse("Stored {$file->name}, but the printer is not connected.");
            }
            if ($this->bridge->hasActiveJob()) {
                return $this->refuse("Stored {$file->name}, but a print is already running.");
            }
            $this->files->print($file);
        }

        return response()->json([
            'files' => [
                'local' => [
                    'name' => $file->name,
                    'origin' => 'local',
                    'path' => $file->name,
                    'refs' => ['resource' => route('printhost.upload').'/'.rawurlencode($file->name)],
                ],
            ],
            'done' => true,
        ], 201);
    }

    private function refuse(string $message): Response
    {
        return response($message, 409)->header('Content-Type', 'text/plain');
    }
}
