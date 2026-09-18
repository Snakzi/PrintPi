<?php

use App\Http\Controllers\PanelSessionController;
use Illuminate\Support\Facades\Route;

// The touch panel's browser signs in with the installer's token, see PanelSessionController.
Route::get('panel/login', [PanelSessionController::class, 'login'])->name('panel.login');

// The Vue app owns every path; vue-router renders the pages client-side.
Route::view('/{any?}', 'app')->where('any', '^(?!api).*$')->name('dashboard');
