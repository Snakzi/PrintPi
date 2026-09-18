<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Laravel\Passkeys\Actions\GenerateVerificationOptions;
use Laravel\Passkeys\Actions\VerifyPasskey;
use Laravel\Passkeys\Http\Requests\PasskeyVerificationRequest;
use Laravel\Passkeys\Support\WebAuthn;

/**
 * Signing in with a passkey: discoverable credentials, so the options name no
 * user and the authenticator offers the accounts it knows for this host.
 */
class PasskeyLoginController extends Controller
{
    public function options(Request $request, GenerateVerificationOptions $generate): JsonResponse
    {
        $options = $generate();
        $request->session()->put('passkey.verification_options', WebAuthn::toJson($options));

        return response()->json(['options' => WebAuthn::toBrowserArray($options)]);
    }

    public function login(PasskeyVerificationRequest $request, VerifyPasskey $verify): JsonResponse
    {
        $passkey = $verify($request->credential(), $request->verificationOptions());

        Auth::guard('web')->login($passkey->user, $request->remember());
        $request->session()->regenerate();
        $user = $request->user();

        return response()->json(['user' => ['name' => $user->name, 'username' => $user->username, 'email' => $user->email]]);
    }
}
