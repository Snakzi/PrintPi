<?php

namespace App\Http\Controllers;

use App\Http\Requests\UpdatePasskeyRequest;
use App\Http\Resources\PasskeyResource;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;
use Illuminate\Http\Response;
use Laravel\Passkeys\Actions\DeletePasskey;
use Laravel\Passkeys\Actions\GenerateRegistrationOptions;
use Laravel\Passkeys\Actions\StorePasskey;
use Laravel\Passkeys\Http\Requests\PasskeyRegistrationRequest;
use Laravel\Passkeys\Passkey;
use Laravel\Passkeys\Support\WebAuthn;

/**
 * The signed-in user's passkeys. Registration is the WebAuthn ceremony in two
 * steps: the options (with the challenge kept in the session) and the credential
 * the browser made from them.
 */
class PasskeyController extends Controller
{
    public function index(Request $request): AnonymousResourceCollection
    {
        return PasskeyResource::collection($request->user()->passkeys()->orderBy('created_at')->get());
    }

    public function options(Request $request, GenerateRegistrationOptions $generate): JsonResponse
    {
        $options = $generate($request->user());
        $request->session()->put('passkey.registration_options', WebAuthn::toJson($options));

        return response()->json(['options' => WebAuthn::toBrowserArray($options)]);
    }

    public function store(PasskeyRegistrationRequest $request, StorePasskey $store): JsonResponse
    {
        $passkey = $store($request->user(), $request->string('name')->toString(), $request->credential(), $request->registrationOptions());

        return (new PasskeyResource($passkey))->response()->setStatusCode(201);
    }

    public function update(UpdatePasskeyRequest $request, int $id): PasskeyResource
    {
        $model = $this->owned($request, $id);
        $model->forceFill(['name' => $request->validated('name')])->save();

        return new PasskeyResource($model);
    }

    public function destroy(Request $request, int $id, DeletePasskey $delete): Response
    {
        $delete($request->user(), $this->owned($request, $id));

        return response()->noContent();
    }

    private function owned(Request $request, int $id): Passkey
    {
        return $request->user()->passkeys()->findOrFail($id);
    }
}
