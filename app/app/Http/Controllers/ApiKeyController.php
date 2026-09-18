<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * The signed-in user's key for the upload API slicers use.
 */
class ApiKeyController extends Controller
{
    public function show(Request $request): JsonResponse
    {
        return response()->json(['api_key' => $request->user()->api_key]);
    }

    public function store(Request $request): JsonResponse
    {
        return response()->json(['api_key' => $request->user()->regenerateApiKey()]);
    }
}
