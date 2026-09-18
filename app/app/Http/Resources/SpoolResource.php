<?php

namespace App\Http\Resources;

use App\Models\Spool;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * @mixin Spool
 */
class SpoolResource extends JsonResource
{
    /**
     * @return array<string, mixed>
     */
    public function toArray(Request $request): array
    {
        $remaining = $this->remaining();

        return [
            'id' => $this->id,
            'name' => $this->name,
            'vendor' => $this->vendor,
            'material' => $this->material,
            'color' => $this->color,
            'finish' => $this->finish,
            'diameter' => $this->diameter,
            'density' => $this->density,
            'weight' => $this->weight,
            'spool_weight' => $this->spool_weight,
            'used' => round($this->used, 2),
            'remaining' => $remaining,
            'remaining_mm' => $this->millimetresFor($remaining),
            'price' => $this->price,
            'loaded' => $this->loaded,
            'archived_at' => $this->archived_at?->toIso8601String(),
            'created_at' => $this->created_at?->toIso8601String(),
        ];
    }
}
