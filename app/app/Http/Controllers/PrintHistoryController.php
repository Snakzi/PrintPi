<?php

namespace App\Http\Controllers;

use App\Http\Requests\UpdatePrintJobRequest;
use App\Http\Resources\PrintJobResource;
use App\Models\PrintJob;
use App\Models\Spool;
use App\Services\FilamentInventory;
use App\Services\PrintHistory;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Storage;
use Symfony\Component\HttpFoundation\BinaryFileResponse;
use Symfony\Component\HttpFoundation\StreamedResponse;

/**
 * Past prints with their postcard material: thumbnail, cover photo and timelapse.
 */
class PrintHistoryController extends Controller
{
    private const string CACHE = 'private, max-age=31536000, immutable';

    public function __construct(
        private readonly PrintHistory $history,
        private readonly FilamentInventory $inventory,
    ) {}

    public function index(Request $request): AnonymousResourceCollection
    {
        $this->history->sync();
        $query = PrintJob::query()->with(['gcodeFile', 'spool'])->latest('started_at')->latest('id');
        if ($request->filled('key')) {
            $query->where('key', $request->string('key')->toString());
        }

        return PrintJobResource::collection($query->limit(100)->get());
    }

    public function show(PrintJob $printJob): PrintJobResource
    {
        return PrintJobResource::make($printJob->load(['gcodeFile', 'spool']));
    }

    /**
     * Books the print on another spool, or on none; the filament it used moves along.
     */
    public function update(UpdatePrintJobRequest $request, PrintJob $printJob): PrintJobResource
    {
        $spoolId = $request->validated('spool_id');
        $this->inventory->assign($printJob, $spoolId === null ? null : Spool::query()->findOrFail($spoolId));

        return PrintJobResource::make($printJob->load(['gcodeFile', 'spool']));
    }

    public function destroy(PrintJob $printJob): Response
    {
        $this->history->delete($printJob);

        return response()->noContent();
    }

    public function thumbnail(PrintJob $printJob): StreamedResponse
    {
        abort_if($printJob->thumbnail === null, 404);

        return Storage::disk(PrintHistory::DISK)->response($printJob->thumbnail, null, ['Cache-Control' => self::CACHE]);
    }

    public function cover(PrintJob $printJob): BinaryFileResponse
    {
        return $this->timelapseFile($printJob->cover, 'image/jpeg');
    }

    public function timelapse(PrintJob $printJob): BinaryFileResponse
    {
        return $this->timelapseFile($printJob->timelapse, 'image/gif');
    }

    public function video(PrintJob $printJob): BinaryFileResponse
    {
        return $this->timelapseFile($printJob->video, 'video/mp4');
    }

    private function timelapseFile(?string $relative, string $contentType): BinaryFileResponse
    {
        $path = $this->history->timelapseFile($relative);
        abort_if($path === null, 404);

        return response()->file($path, ['Content-Type' => $contentType, 'Cache-Control' => self::CACHE]);
    }
}
