<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class FlashFirmwareRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /**
     * `name` is a file on the printer's drive (Buddy), `file` an upload and `source`
     * "release" the newest published firmware (avrdude); which one applies is the
     * controller's call, since the method comes from the settings.
     *
     * @return array<string, list<mixed>>
     */
    public function rules(): array
    {
        return [
            'name' => ['sometimes', 'nullable', 'string', 'regex:/^[A-Za-z0-9._~+-]{1,64}$/'],
            'file' => ['sometimes', 'file', 'extensions:hex,bin', 'max:8192'],
            'source' => ['sometimes', 'nullable', Rule::in(['upload', 'release'])],
        ];
    }
}
