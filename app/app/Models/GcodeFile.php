<?php

namespace App\Models;

use Database\Factories\GcodeFileFactory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class GcodeFile extends Model
{
    /** @use HasFactory<GcodeFileFactory> */
    use HasFactory;

    protected $fillable = ['name', 'size', 'metadata', 'thumbnail'];

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'size' => 'integer',
            'metadata' => 'array',
        ];
    }
}
