<?php

namespace App\Models;

use Database\Factories\PrintJobFactory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * One run of a print job, filed from the daemon's record when it ended.
 */
class PrintJob extends Model
{
    /** @use HasFactory<PrintJobFactory> */
    use HasFactory;

    protected $fillable = [
        'key', 'gcode_file_id', 'spool_id', 'name', 'state', 'error', 'started_at', 'finished_at', 'elapsed', 'progress',
        'layers', 'total_layers', 'filament_g', 'filament_mm', 'slicer', 'printer', 'thumbnail', 'cover',
        'timelapse', 'video', 'frames', 'energy_wh',
    ];

    /**
     * @return BelongsTo<GcodeFile, $this>
     */
    public function gcodeFile(): BelongsTo
    {
        return $this->belongsTo(GcodeFile::class);
    }

    /**
     * @return BelongsTo<Spool, $this>
     */
    public function spool(): BelongsTo
    {
        return $this->belongsTo(Spool::class);
    }

    /**
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'started_at' => 'datetime',
            'finished_at' => 'datetime',
            'elapsed' => 'integer',
            'progress' => 'float',
            'layers' => 'integer',
            'total_layers' => 'integer',
            'filament_g' => 'float',
            'filament_mm' => 'float',
            'frames' => 'integer',
            'energy_wh' => 'float',
        ];
    }
}
