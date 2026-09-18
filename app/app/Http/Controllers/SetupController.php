<?php

namespace App\Http\Controllers;

use App\Http\Requests\StoreSetupRequest;
use App\Models\User;
use App\Services\PrinterBridge;
use App\Services\PrinterCatalog;
use App\Services\Settings;
use App\Services\SystemControl;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Auth;

class SetupController extends Controller
{
    public function __construct(
        private readonly PrinterBridge $bridge,
        private readonly PrinterCatalog $catalog,
        private readonly Settings $settings,
        private readonly SystemControl $system,
    ) {}

    /**
     * Everything the setup wizard needs before an account exists.
     */
    public function show(): JsonResponse
    {
        $webcam = rtrim((string) config('printpi.webcam_base'), '/');

        return response()->json([
            'hostname' => $this->settings->get('hostname') ?? $this->system->hostname(),
            'timezone' => $this->settings->get('timezone'),
            'system_control' => $this->system->available(),
            'daemon_alive' => $this->bridge->isDaemonAlive(),
            'printers' => $this->catalog->all(),
            'ports' => $this->bridge->ports(),
            'cameras' => $this->bridge->cameras(),
            'camera' => $this->bridge->camera(),
            'stream_url' => $webcam.'/stream',
            'snapshot_url' => $webcam.'/snapshot',
        ]);
    }

    public function store(StoreSetupRequest $request): JsonResponse
    {
        $data = $request->validated();

        $user = User::query()->create([
            'name' => $data['username'],
            'username' => $data['username'],
            'email' => strtolower($data['email']),
            'password' => $data['password'],
            'api_key' => User::newApiKey(),
        ]);

        $settings = $this->settings->set([
            'hostname' => $data['hostname'],
            'timezone' => $data['timezone'],
            'printer_profile' => $data['printer_profile'],
            'printer_name' => $data['printer_name'],
            'serial_port' => $data['serial_port'] ?? null,
            'baud_rate' => (int) $data['baud_rate'],
            'camera_device' => $data['camera_device'] ?? null,
            'camera_url' => $data['camera_url'] ?? null,
        ]);

        $hostnameApplied = $this->system->setHostname($data['hostname']);
        $timezoneApplied = $this->system->setTimezone($data['timezone']);

        if (! empty($data['camera_device'])) {
            $this->bridge->startCamera($data['camera_device']);
        } else {
            $this->bridge->stopCamera();
        }

        Auth::login($user);
        $request->session()->regenerate();

        return response()->json([
            'user' => ['name' => $user->name, 'username' => $user->username, 'email' => $user->email],
            'settings' => $settings,
            'hostname_applied' => $hostnameApplied,
            'timezone_applied' => $timezoneApplied,
        ], 201);
    }
}
