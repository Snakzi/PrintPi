<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class StartUpdateRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /** @return array<string, list<string>> */
    public function rules(): array
    {
        return [
            'version' => ['required', 'string', 'regex:/^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$/'],
        ];
    }
}
