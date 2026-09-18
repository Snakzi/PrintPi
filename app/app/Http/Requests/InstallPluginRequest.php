<?php

namespace App\Http\Requests;

use App\Services\PluginManifest;
use Illuminate\Foundation\Http\FormRequest;

/**
 * Either the id of a plugin the catalog knows or the https URL of a git repository.
 */
class InstallPluginRequest extends FormRequest
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
            'id' => ['required_without:url', 'nullable', 'string', 'regex:'.PluginManifest::ID_PATTERN],
            'url' => ['required_without:id', 'nullable', 'string', 'max:500', 'regex:#^https://[A-Za-z0-9.-]+(/[A-Za-z0-9._~-]+){2,}/?$#'],
        ];
    }
}
