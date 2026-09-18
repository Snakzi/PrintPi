<?php

use App\Http\Middleware\AuthenticateWithApiKey;
use Illuminate\Cookie\Middleware\AddQueuedCookiesToResponse;
use Illuminate\Cookie\Middleware\EncryptCookies;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Foundation\Http\Middleware\ValidateCsrfToken;
use Illuminate\Http\Request;
use Illuminate\Session\Middleware\StartSession;
use Illuminate\Support\Facades\Route;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
        // The print host endpoints slicers upload to carry an API key instead of
        // the session cookie, so they stay out of the api group and its CSRF check.
        then: function (): void {
            Route::middleware(AuthenticateWithApiKey::class)->prefix('api')->group(__DIR__.'/../routes/printhost.php');
        },
    )
    ->withMiddleware(function (Middleware $middleware): void {
        // The Vue app lives on the same origin, so the API authenticates with the
        // session cookie and checks the XSRF-TOKEN cookie on writes.
        $middleware->api(prepend: [
            EncryptCookies::class,
            AddQueuedCookiesToResponse::class,
            StartSession::class,
            ValidateCsrfToken::class,
        ]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->shouldRenderJsonWhen(
            fn (Request $request) => $request->is('api/*') || $request->expectsJson(),
        );
    })->create();
