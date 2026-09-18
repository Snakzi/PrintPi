<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class SendGcodeRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /**
     * One G-code command per request. Line breaks are rejected so a single
     * request can never smuggle a second command past the daemon's queue.
     *
     * @return array<string, list<string>>
     */
    public function rules(): array
    {
        return [
            'command' => ['required', 'string', 'max:200', 'regex:/^[^\r\n]+$/'],
        ];
    }
}
