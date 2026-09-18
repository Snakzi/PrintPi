<?php

namespace App\Http\Controllers;

use App\Http\Requests\SpoolRequest;
use App\Http\Resources\SpoolResource;
use App\Models\Spool;
use App\Services\FilamentInventory;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;
use Illuminate\Http\Response;

/**
 * The filament inventory: spools, what is left on them and which one is in the printer.
 */
class SpoolController extends Controller
{
    public function __construct(private readonly FilamentInventory $inventory) {}

    /**
     * Every spool, the loaded one first.
     */
    public function index(): AnonymousResourceCollection
    {
        return SpoolResource::collection(Spool::query()->orderByDesc('loaded')->orderBy('archived_at')->latest('id')->get());
    }

    /**
     * What the form offers: materials with their density, the finishes a spool can have, vendors with
     * their empty spool weight and product lines.
     */
    public function catalog(): JsonResponse
    {
        return response()->json([
            'materials' => config('filament.materials'),
            'finishes' => config('filament.finishes'),
            'vendors' => config('filament.vendors'),
        ]);
    }

    public function store(SpoolRequest $request): JsonResponse
    {
        $spool = $this->inventory->create($request->validated());

        return SpoolResource::make($spool)->response()->setStatusCode(201);
    }

    public function update(SpoolRequest $request, Spool $spool): SpoolResource
    {
        return SpoolResource::make($this->inventory->update($spool, $request->validated()));
    }

    public function destroy(Spool $spool): Response
    {
        $spool->delete();

        return response()->noContent();
    }

    public function load(Spool $spool): SpoolResource
    {
        return SpoolResource::make($this->inventory->load($spool));
    }

    public function unload(): Response
    {
        $this->inventory->unload();

        return response()->noContent();
    }
}
