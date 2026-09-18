<?php

use App\Http\Controllers\PrintHostController;
use Illuminate\Support\Facades\Route;

// What a slicer's print host talks to; authenticated by API key, see bootstrap/app.php.
Route::get('version', [PrintHostController::class, 'version'])->name('printhost.version');
Route::post('files/local', [PrintHostController::class, 'upload'])->name('printhost.upload');
