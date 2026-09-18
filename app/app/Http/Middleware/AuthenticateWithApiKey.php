<?php

namespace App\Http\Middleware;

use App\Models\User;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Symfony\Component\HttpFoundation\Response;

/**
 * Authenticates a slicer's request by the X-Api-Key header slicers send;
 * the answer is plain text because the slicer shows the body of an error as is.
 */
class AuthenticateWithApiKey
{
    public function handle(Request $request, Closure $next): Response
    {
        $key = $request->header('X-Api-Key');
        $user = is_string($key) && $key !== '' ? User::query()->where('api_key', $key)->first() : null;
        if ($user === null) {
            return response('Invalid API key', 403)->header('Content-Type', 'text/plain');
        }
        Auth::setUser($user);

        return $next($request);
    }
}
