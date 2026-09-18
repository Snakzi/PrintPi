<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class FilamentAnswerRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /**
     * The answer to the colour check: the filament runs clean, or purge some more.
     *
     * @return array<string, list<mixed>>
     */
    public function rules(): array
    {
        return [
            'answer' => ['required', Rule::in(['yes', 'purge'])],
        ];
    }
}
