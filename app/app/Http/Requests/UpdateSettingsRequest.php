<?php

namespace App\Http\Requests;

use App\Services\Firmware;
use App\Services\PrinterCatalog;
use App\Services\Settings;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class UpdateSettingsRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /**
     * @return array<string, list<mixed>>
     */
    public function rules(): array
    {
        return [
            'serial_port' => ['sometimes', 'nullable', 'string', 'max:200'],
            'baud_rate' => ['sometimes', 'integer', Rule::in(Settings::BAUD_RATES)],
            'camera_device' => ['sometimes', 'nullable', 'string', 'max:200', 'regex:#^/dev/video\d+$#'],
            'camera_url' => ['sometimes', 'nullable', 'string', 'max:500'],
            'hostname' => ['sometimes', 'string', 'max:63', 'regex:/^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/'],
            'timezone' => ['sometimes', 'timezone:all'],
            'update_channel' => ['sometimes', Rule::in(config('printpi.update_channels'))],
            'printer_profile' => ['sometimes', 'string', Rule::in(app(PrinterCatalog::class)->supportedIds())],
            'printer_name' => ['sometimes', 'nullable', 'string', 'max:100'],
            'energy_price' => ['sometimes', 'nullable', 'numeric', 'min:0', 'max:100'],
            'currency' => ['sometimes', 'string', 'max:5'],
            'firmware_method' => ['sometimes', 'nullable', Rule::in(Firmware::METHODS)],
            'firmware_mcu' => ['sometimes', 'nullable', 'string', 'regex:/^[a-z0-9]{1,32}$/'],
            'firmware_programmer' => ['sometimes', 'nullable', 'string', 'regex:/^[a-z0-9_-]{1,32}$/'],
            'firmware_baud' => ['sometimes', 'nullable', 'integer', Rule::in(Settings::BAUD_RATES)],
            'macros' => ['sometimes', 'array', 'max:20'],
            'macros.*.label' => ['required', 'string', 'max:30'],
            'macros.*.gcode' => ['required', 'string', 'max:2000'],
            'timelapse' => ['sometimes', 'boolean'],
            'timelapse_gif' => ['sometimes', 'boolean'],
            'timelapse_mp4' => ['sometimes', 'boolean'],
            'postcard' => ['sometimes', 'boolean'],
            'cancel_gcode' => ['sometimes', 'nullable', 'string', 'max:2000'],
            'history_keep' => ['sometimes', 'integer', 'min:0', 'max:10000'],
            'notify_print_end' => ['sometimes', 'boolean'],
            'notify_plugins' => ['sometimes', 'boolean'],
            'tab_progress' => ['sometimes', 'boolean'],
        ];
    }
}
