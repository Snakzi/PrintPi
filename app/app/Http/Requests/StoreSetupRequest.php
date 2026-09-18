<?php

namespace App\Http\Requests;

use App\Services\PrinterCatalog;
use App\Services\Settings;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;
use Illuminate\Validation\Rules\Password;

class StoreSetupRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /**
     * @return array<string, list<mixed>>
     */
    public function rules(PrinterCatalog $catalog): array
    {
        return [
            'username' => ['required', 'string', 'min:3', 'max:50', 'regex:/^[a-z0-9._-]+$/i'],
            'email' => ['required', 'string', 'email', 'max:255'],
            'password' => ['required', 'confirmed', Password::min(8)],
            'hostname' => ['required', 'string', 'max:63', 'regex:/^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/'],
            'timezone' => ['required', 'timezone:all'],
            'printer_profile' => ['required', 'string', Rule::in($catalog->supportedIds())],
            'printer_name' => ['required', 'string', 'max:100'],
            'serial_port' => ['nullable', 'string', 'max:200'],
            'baud_rate' => ['required', 'integer', Rule::in(Settings::BAUD_RATES)],
            'camera_device' => ['nullable', 'string', 'max:200', 'regex:#^/dev/video\d+$#'],
            'camera_url' => ['nullable', 'string', 'max:500'],
        ];
    }
}
