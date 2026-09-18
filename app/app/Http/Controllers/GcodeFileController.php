<?php

namespace App\Http\Controllers;

use App\Http\Requests\StoreGcodeFileRequest;
use App\Http\Resources\GcodeFileResource;
use App\Models\GcodeFile;
use App\Services\GcodeFiles;
use App\Services\PrinterBridge;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;
use Illuminate\Http\Response;
use Symfony\Component\HttpFoundation\StreamedResponse;

class GcodeFileController extends Controller
{
    public function __construct(private readonly GcodeFiles $files) {}

    public function index(): AnonymousResourceCollection
    {
        return GcodeFileResource::collection(GcodeFile::query()->latest('updated_at')->get());
    }

    public function store(StoreGcodeFileRequest $request): JsonResponse
    {
        $upload = $request->file('file');
        abort_if($this->files->isBeingPrinted($this->files->safeName($upload->getClientOriginalName())), 409, 'This file is being printed right now.');

        return GcodeFileResource::make($this->files->store($upload))->response()->setStatusCode(201);
    }

    public function destroy(GcodeFile $gcodeFile): Response
    {
        $this->files->delete($gcodeFile);

        return response()->noContent();
    }

    public function download(GcodeFile $gcodeFile): StreamedResponse
    {
        return $this->files->disk()->download($gcodeFile->name, $gcodeFile->name, ['Content-Type' => 'text/plain; charset=utf-8']);
    }

    public function thumbnail(GcodeFile $gcodeFile): StreamedResponse
    {
        abort_if($gcodeFile->thumbnail === null, 404);

        return $this->files->disk()->response($gcodeFile->thumbnail, null, ['Cache-Control' => 'private, max-age=86400']);
    }

    public function print(GcodeFile $gcodeFile, PrinterBridge $bridge): JsonResponse
    {
        abort_unless($bridge->isConnected(), 409, 'The printer is not connected.');
        abort_if($bridge->hasActiveJob(), 409, 'A print is already running.');

        $this->files->print($gcodeFile);

        return response()->json(['queued' => true], 202);
    }
}
