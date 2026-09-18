<?php

namespace App\Http\Controllers;

use App\Services\PrinterCatalog;
use Illuminate\Http\JsonResponse;

class PrinterProfileController extends Controller
{
    public function index(PrinterCatalog $catalog): JsonResponse
    {
        return response()->json(['data' => $catalog->all()]);
    }
}
