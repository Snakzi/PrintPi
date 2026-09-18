<?php

namespace App\Http\Requests;

use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;

/**
 * The same rules as the dashboard upload, answered as a plain sentence the slicer can show.
 */
class PrintHostUploadRequest extends StoreGcodeFileRequest
{
    protected function failedValidation(Validator $validator): never
    {
        throw new HttpResponseException(response($validator->errors()->first(), 422)->header('Content-Type', 'text/plain'));
    }
}
