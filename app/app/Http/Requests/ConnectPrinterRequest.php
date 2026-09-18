<?php

namespace App\Http\Requests;

use App\Services\Settings;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class ConnectPrinterRequest extends FormRequest
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
            'port' => ['required', 'string', 'max:200'],
            'baud' => ['required', 'integer', Rule::in(Settings::BAUD_RATES)],
        ];
    }
}
