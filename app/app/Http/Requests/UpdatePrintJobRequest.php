<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

/**
 * What a past print may change afterwards: the spool it is booked on.
 */
class UpdatePrintJobRequest extends FormRequest
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
            'spool_id' => ['present', 'nullable', 'integer', 'exists:spools,id'],
        ];
    }
}
