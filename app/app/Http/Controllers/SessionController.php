<?php

namespace App\Http\Controllers;

use App\Http\Requests\LoginRequest;
use App\Models\User;
use App\Services\SystemControl;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Auth;
use Illuminate\Validation\ValidationException;
use Laravel\Passkeys\Passkey;

class SessionController extends Controller
{
    public function __construct(private readonly SystemControl $system) {}

    public function show(Request $request): JsonResponse
    {
        $user = $request->user();

        return response()->json([
            'setup_complete' => User::query()->exists(),
            'authenticated' => $user !== null,
            'passkeys' => Passkey::query()->exists(),
            'user' => $user ? ['name' => $user->name, 'username' => $user->username, 'email' => $user->email] : null,
            'system_control' => $this->system->available(),
        ]);
    }

    public function login(LoginRequest $request): JsonResponse
    {
        $login = strtolower(trim($request->validated('username')));
        $field = str_contains($login, '@') ? 'email' : 'username';
        // Usernames keep the case they were chosen with, so match them case-insensitively
        // and attempt with the stored value; SQLite compares strings case-sensitively.
        $user = User::query()->whereRaw("lower($field) = ?", [$login])->first();
        if ($user === null || ! Auth::attempt([$field => $user->{$field}, 'password' => $request->validated('password')], (bool) $request->validated('remember', false))) {
            throw ValidationException::withMessages(['username' => __('auth.failed')]);
        }
        $request->session()->regenerate();
        $user = $request->user();

        return response()->json(['user' => ['name' => $user->name, 'username' => $user->username, 'email' => $user->email]]);
    }

    public function logout(Request $request): Response
    {
        Auth::guard('web')->logout();
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return response()->noContent();
    }
}
