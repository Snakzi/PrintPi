<?php

namespace App\Http\Controllers;

use App\Http\Requests\UpdatePasswordRequest;
use App\Http\Requests\UpdateProfileRequest;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Response;

class AccountController extends Controller
{
    /**
     * Username and email of the signed-in user; `name` keeps mirroring the username.
     */
    public function update(UpdateProfileRequest $request): JsonResponse
    {
        $user = $request->user();
        $user->forceFill([
            'name' => $request->validated('username'),
            'username' => $request->validated('username'),
            'email' => strtolower($request->validated('email')),
        ])->save();

        return response()->json(['user' => ['name' => $user->name, 'username' => $user->username, 'email' => $user->email]]);
    }

    public function password(UpdatePasswordRequest $request): Response
    {
        $request->user()->forceFill(['password' => $request->validated('password')])->save();

        return response()->noContent();
    }
}
