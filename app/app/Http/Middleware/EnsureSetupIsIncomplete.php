<?php

namespace App\Http\Middleware;

use App\Models\User;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/**
 * The setup endpoints are open only until the first user exists.
 */
class EnsureSetupIsIncomplete
{
    public function handle(Request $request, Closure $next): Response
    {
        if (User::query()->exists()) {
            abort(403, 'Setup is already complete.');
        }

        return $next($request);
    }
}
