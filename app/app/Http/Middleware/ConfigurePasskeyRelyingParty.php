<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/**
 * A Pi is reached under whatever name the browser used (printpi.local, an IP, a
 * reverse proxy), so the WebAuthn relying party follows the request instead of
 * APP_URL. A passkey is bound to the host it was created on.
 */
class ConfigurePasskeyRelyingParty
{
    public function handle(Request $request, Closure $next): Response
    {
        config([
            'passkeys.relying_party_id' => $request->getHost(),
            'passkeys.allowed_origins' => [$request->getSchemeAndHttpHost()],
        ]);

        return $next($request);
    }
}
