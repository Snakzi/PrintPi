<?php

namespace App\Http\Resources;

use App\Models\GcodeFile;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * @mixin GcodeFile
 */
class GcodeFileResource extends JsonResource
{
    /**
     * @return array<string, mixed>
     */
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'size' => $this->size,
            'metadata' => $this->metadata ?? [],
            'thumbnail_url' => $this->thumbnailUrl(),
            'download_url' => route('files.download', $this->resource, false),
            'uploaded_at' => $this->updated_at?->toIso8601String(),
        ];
    }

    /**
     * Versioned by the upload time so a replaced file is not served from the browser cache.
     */
    private function thumbnailUrl(): ?string
    {
        if ($this->thumbnail === null) {
            return null;
        }

        return route('files.thumbnail', $this->resource, false).'?v='.($this->updated_at?->getTimestamp() ?? 0);
    }
}
