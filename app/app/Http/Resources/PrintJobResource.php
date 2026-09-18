<?php

namespace App\Http\Resources;

use App\Models\PrintJob;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * @mixin PrintJob
 */
class PrintJobResource extends JsonResource
{
    /**
     * @return array<string, mixed>
     */
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'key' => $this->key,
            'name' => $this->name,
            'state' => $this->state,
            'error' => $this->error,
            'started_at' => $this->started_at?->toIso8601String(),
            'finished_at' => $this->finished_at?->toIso8601String(),
            'elapsed' => $this->elapsed,
            'progress' => $this->progress,
            'layers' => $this->layers,
            'total_layers' => $this->total_layers,
            'filament_g' => $this->filament_g,
            'filament_mm' => $this->filament_mm,
            'slicer' => $this->slicer,
            'printer' => $this->printer,
            'energy_wh' => $this->energy_wh,
            'frames' => $this->frames,
            'thumbnail_url' => $this->thumbnail !== null ? route('prints.thumbnail', $this->resource, false) : null,
            'cover_url' => $this->cover !== null ? route('prints.cover', $this->resource, false) : null,
            'timelapse_url' => $this->timelapse !== null ? route('prints.timelapse', $this->resource, false) : null,
            'video_url' => $this->video !== null ? route('prints.video', $this->resource, false) : null,
            'file' => $this->gcodeFile !== null ? ['id' => $this->gcodeFile->id, 'name' => $this->gcodeFile->name] : null,
            'spool' => $this->spool !== null ? [
                'id' => $this->spool->id,
                'name' => $this->spool->name,
                'vendor' => $this->spool->vendor,
                'material' => $this->spool->material,
                'color' => $this->spool->color,
                'finish' => $this->spool->finish,
            ] : null,
            'filament_cost' => $this->filamentCost(),
        ];
    }

    /**
     * What the filament cost at the spool's price, or null without a price or a weight.
     */
    private function filamentCost(): ?float
    {
        $spool = $this->spool;
        if ($spool === null || $spool->price === null || $spool->weight <= 0 || $this->filament_g === null) {
            return null;
        }

        return round($this->filament_g / $spool->weight * $spool->price, 2);
    }
}
