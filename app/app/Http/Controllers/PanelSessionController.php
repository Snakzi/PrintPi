<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

/**
 * Signs the kiosk browser on the Pi's own screen in without a keyboard: it opens
 * /panel/login?token=… with the token the installer wrote into app.env and panel.env.
 * Only loopback may use it, and only while a token is configured.
 */
class PanelSessionController extends Controller
{
    public function login(Request $request): RedirectResponse
    {
        $token = config('printpi.panel_token');
        abort_unless(is_string($token) && $token !== '', 404);
        abort_unless(in_array($request->ip(), ['127.0.0.1', '::1'], true), 403);
        abort_unless(hash_equals($token, (string) $request->query('token', '')), 403);

        $user = User::query()->orderBy('id')->first();
        abort_if($user === null, 404);

        Auth::guard('web')->login($user, true);
        $request->session()->regenerate();

        return redirect('/panel');
    }
}
