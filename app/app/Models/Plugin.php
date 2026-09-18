<?php

namespace App\Models;

use Database\Factories\PluginFactory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

/**
 * Install state of a plugin; the manifest itself lives in the plugin directory.
 */
class Plugin extends Model
{
    /** @use HasFactory<PluginFactory> */
    use HasFactory;

    public const string SOURCE_BUILTIN = 'builtin';

    public const string SOURCE_GIT = 'git';

    protected $primaryKey = 'id';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $fillable = ['id', 'source', 'url', 'version', 'enabled', 'settings'];

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'enabled' => 'boolean',
            'settings' => 'array',
        ];
    }
}
