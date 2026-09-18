<?php

namespace App\Http\Controllers;

use App\Http\Requests\UpdateSettingsRequest;
use App\Services\Settings;
use App\Services\SystemControl;
use Illuminate\Http\JsonResponse;

class SettingsController extends Controller
{
    public function __construct(
        private readonly Settings $settings,
        private readonly SystemControl $system,
    ) {}

    public function show(): JsonResponse
    {
        return response()->json($this->settings->all());
    }

    public function update(UpdateSettingsRequest $request): JsonResponse
    {
        $data = $request->validated();
        $values = $this->settings->set($data);

        if (array_key_exists('hostname', $data)) {
            $this->system->setHostname($data['hostname']);
        }
        if (array_key_exists('timezone', $data)) {
            $this->system->setTimezone($data['timezone']);
        }

        return response()->json($values);
    }
}
