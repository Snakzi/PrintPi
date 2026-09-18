<?php

namespace App\Http\Requests;

use App\Services\PluginManifest;
use Closure;
use Illuminate\Foundation\Http\FormRequest;

class PluginActionRequest extends FormRequest
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
            'action' => ['required', 'string', 'regex:'.PluginManifest::KEY_PATTERN],
            'value' => ['nullable', function (string $attribute, mixed $value, Closure $fail): void {
                $flat = is_array($value) && array_all($value, fn (mixed $item): bool => $item === null || is_scalar($item));

                if (! is_scalar($value) && ! $flat) {
                    $fail('The value must be a number, a string, a boolean or an object of those.');
                }
            }],
        ];
    }
}
