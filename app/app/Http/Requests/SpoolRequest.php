<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

/**
 * A spool as the form sends it, for creating and for editing. `remaining` stands
 * in for the stored `used`, which is what a user reads off a scale.
 */
class SpoolRequest extends FormRequest
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
        $required = $this->isMethod('POST') ? 'required' : 'sometimes';

        return [
            'name' => [$required, 'string', 'max:100'],
            'vendor' => ['sometimes', 'nullable', 'string', 'max:100'],
            'material' => [$required, 'string', 'max:40'],
            'color' => ['sometimes', 'nullable', 'string', 'regex:/^#[0-9a-fA-F]{6}$/'],
            'finish' => ['sometimes', 'nullable', 'string', Rule::in(config('filament.finishes'))],
            'diameter' => ['sometimes', 'numeric', 'between:1,3.5'],
            'density' => ['sometimes', 'numeric', 'between:0.5,3'],
            'weight' => ['sometimes', 'numeric', 'between:1,20000'],
            'spool_weight' => ['sometimes', 'nullable', 'numeric', 'between:0,5000'],
            'remaining' => ['sometimes', 'numeric', 'between:0,20000'],
            'price' => ['sometimes', 'nullable', 'numeric', 'between:0,100000'],
            'archived' => ['sometimes', 'boolean'],
        ];
    }

    protected function prepareForValidation(): void
    {
        $this->merge(array_map(
            static fn (mixed $value): mixed => is_string($value) ? (trim($value) === '' ? null : trim($value)) : $value,
            $this->only(['name', 'vendor', 'material', 'color', 'finish']),
        ));
    }
}
