<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

/**
 * What to load: a spool of the inventory, or just a material for filament that is not in it.
 * unload_first turns the load into a change, for a printer that still has filament in it.
 */
class FilamentLoadRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /**
     * @return array<string, list<string>>
     */
    public function rules(): array
    {
        return [
            'spool_id' => ['nullable', 'integer', 'exists:spools,id', 'required_without:material'],
            'material' => ['nullable', 'string', 'max:40', 'required_without:spool_id'],
            'unload_first' => ['sometimes', 'boolean'],
        ];
    }
}
