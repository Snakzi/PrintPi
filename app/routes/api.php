<?php

use App\Http\Controllers\AccountController;
use App\Http\Controllers\ApiKeyController;
use App\Http\Controllers\CameraController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\FilamentChangeController;
use App\Http\Controllers\FirmwareController;
use App\Http\Controllers\GcodeFileController;
use App\Http\Controllers\PasskeyController;
use App\Http\Controllers\PasskeyLoginController;
use App\Http\Controllers\PluginController;
use App\Http\Controllers\PrinterController;
use App\Http\Controllers\PrinterProfileController;
use App\Http\Controllers\PrintHistoryController;
use App\Http\Controllers\PrintJobController;
use App\Http\Controllers\SessionController;
use App\Http\Controllers\SettingsController;
use App\Http\Controllers\SetupController;
use App\Http\Controllers\SpoolController;
use App\Http\Controllers\SystemController;
use App\Http\Controllers\UpdateController;
use App\Http\Middleware\ConfigurePasskeyRelyingParty;
use App\Http\Middleware\EnsureSetupIsIncomplete;
use Illuminate\Support\Facades\Route;

Route::pattern('plugin', '[a-z0-9][a-z0-9_-]*');

Route::prefix('v1')->group(function (): void {
    Route::get('session', [SessionController::class, 'show'])->name('session.show');
    Route::post('login', [SessionController::class, 'login'])->middleware('throttle:10,1')->name('session.login');
    Route::post('logout', [SessionController::class, 'logout'])->middleware('auth')->name('session.logout');

    // Passkeys: the relying party follows the host the browser used, see the middleware.
    Route::middleware(ConfigurePasskeyRelyingParty::class)->prefix('passkeys')->name('passkeys.')->group(function (): void {
        Route::get('login/options', [PasskeyLoginController::class, 'options'])->middleware('throttle:10,1')->name('login.options');
        Route::post('login', [PasskeyLoginController::class, 'login'])->middleware('throttle:10,1')->name('login');

        Route::middleware('auth')->controller(PasskeyController::class)->group(function (): void {
            Route::get('/', 'index')->name('index');
            Route::get('options', 'options')->name('options');
            Route::post('/', 'store')->name('store');
            Route::put('{id}', 'update')->whereNumber('id')->name('update');
            Route::delete('{id}', 'destroy')->whereNumber('id')->name('destroy');
        });
    });

    // Open only until the first user exists: the setup wizard.
    Route::middleware(EnsureSetupIsIncomplete::class)->prefix('setup')->name('setup.')->group(function (): void {
        Route::get('/', [SetupController::class, 'show'])->name('show');
        Route::post('/', [SetupController::class, 'store'])->name('store');
        Route::get('camera', [CameraController::class, 'show'])->name('camera.show');
        Route::post('camera/start', [CameraController::class, 'start'])->name('camera.start');
        Route::post('camera/stop', [CameraController::class, 'stop'])->name('camera.stop');
    });

    Route::middleware('auth')->group(function (): void {
        Route::prefix('printer')->name('printer.')->controller(PrinterController::class)->group(function (): void {
            Route::get('state', 'state')->name('state');
            Route::get('serial', 'serial')->name('serial');
            Route::post('command', 'command')->name('command');
            Route::post('connect', 'connect')->name('connect');
            Route::post('reconnect', 'reconnect')->name('reconnect');
            Route::post('disconnect', 'disconnect')->name('disconnect');
            Route::post('emergency-stop', 'emergencyStop')->name('emergency-stop');

            Route::prefix('job')->name('job.')->controller(PrintJobController::class)->group(function (): void {
                Route::post('pause', 'pause')->name('pause');
                Route::post('resume', 'resume')->name('resume');
                Route::post('cancel', 'cancel')->name('cancel');
                Route::post('restart', 'restart')->name('restart');
            });

            Route::prefix('filament')->name('filament.')->controller(FilamentChangeController::class)->group(function (): void {
                Route::post('load', 'load')->name('load');
                Route::post('unload', 'unload')->name('unload');
                Route::post('continue', 'proceed')->name('continue');
                Route::post('answer', 'answer')->name('answer');
                Route::post('cancel', 'cancel')->name('cancel');
            });

            Route::prefix('firmware')->name('firmware.')->controller(FirmwareController::class)->group(function (): void {
                Route::get('/', 'show')->name('show');
                Route::post('files', 'files')->name('files');
                Route::post('flash', 'flash')->name('flash');
            });
        });

        Route::apiResource('files', GcodeFileController::class)
            ->only(['index', 'store', 'destroy'])
            ->parameters(['files' => 'gcodeFile']);
        Route::post('files/{gcodeFile}/print', [GcodeFileController::class, 'print'])->name('files.print');
        Route::get('files/{gcodeFile}/download', [GcodeFileController::class, 'download'])->name('files.download');
        Route::get('files/{gcodeFile}/thumbnail', [GcodeFileController::class, 'thumbnail'])->name('files.thumbnail');

        Route::get('printers', [PrinterProfileController::class, 'index'])->name('printers.index');

        Route::prefix('prints')->name('prints.')->controller(PrintHistoryController::class)->group(function (): void {
            Route::get('/', 'index')->name('index');
            Route::get('{printJob}', 'show')->name('show');
            Route::put('{printJob}', 'update')->name('update');
            Route::delete('{printJob}', 'destroy')->name('destroy');
            Route::get('{printJob}/thumbnail', 'thumbnail')->name('thumbnail');
            Route::get('{printJob}/cover', 'cover')->name('cover');
            Route::get('{printJob}/timelapse', 'timelapse')->name('timelapse');
            Route::get('{printJob}/video', 'video')->name('video');
        });

        Route::prefix('spools')->name('spools.')->controller(SpoolController::class)->group(function (): void {
            Route::get('/', 'index')->name('index');
            Route::get('catalog', 'catalog')->name('catalog');
            Route::post('/', 'store')->name('store');
            Route::post('unload', 'unload')->name('unload');
            Route::put('{spool}', 'update')->name('update');
            Route::delete('{spool}', 'destroy')->name('destroy');
            Route::post('{spool}/load', 'load')->name('load');
        });

        Route::get('camera', [CameraController::class, 'show'])->name('camera.show');
        Route::post('camera/start', [CameraController::class, 'start'])->name('camera.start');
        Route::post('camera/stop', [CameraController::class, 'stop'])->name('camera.stop');

        Route::prefix('plugins')->name('plugins.')->controller(PluginController::class)->group(function (): void {
            Route::get('/', 'index')->name('index');
            Route::post('/', 'store')->name('store');
            Route::put('{plugin}', 'update')->name('update');
            Route::delete('{plugin}', 'destroy')->name('destroy');
            Route::put('{plugin}/settings', 'updateSettings')->name('settings');
            Route::post('{plugin}/actions', 'action')->name('action');
            Route::post('{plugin}/upgrade', 'upgrade')->name('upgrade');
        });

        Route::put('account', [AccountController::class, 'update'])->name('account.update');
        Route::put('account/password', [AccountController::class, 'password'])->name('account.password');

        Route::get('api-key', [ApiKeyController::class, 'show'])->name('api-key.show');
        Route::post('api-key', [ApiKeyController::class, 'store'])->name('api-key.store');

        Route::get('settings', [SettingsController::class, 'show'])->name('settings.show');
        Route::put('settings', [SettingsController::class, 'update'])->name('settings.update');

        Route::post('system/reboot', [SystemController::class, 'reboot'])->name('system.reboot');
        Route::post('system/restart-web', [SystemController::class, 'restartWebServer'])->name('system.restart-web');
        Route::get('system/history', [SystemController::class, 'history'])->name('system.history');

        Route::get('system/update', [UpdateController::class, 'show'])->name('system.update.show');
        Route::post('system/update', [UpdateController::class, 'start'])->name('system.update.start');
        Route::post('system/update/rollback', [UpdateController::class, 'rollback'])->name('system.update.rollback');

        Route::get('dashboard', [DashboardController::class, 'show'])->name('dashboard.show');
        Route::put('dashboard', [DashboardController::class, 'update'])->name('dashboard.update');
        Route::delete('dashboard', [DashboardController::class, 'destroy'])->name('dashboard.reset');
    });
});
