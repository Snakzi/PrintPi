<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('print_jobs', function (Blueprint $table): void {
            $table->id();
            $table->string('key', 32)->unique();
            $table->foreignId('gcode_file_id')->nullable()->constrained()->nullOnDelete();
            $table->string('name');
            $table->string('state', 20);
            $table->text('error')->nullable();
            $table->timestamp('started_at');
            $table->timestamp('finished_at')->nullable();
            $table->unsignedInteger('elapsed')->default(0);
            $table->float('progress')->default(0);
            $table->unsignedInteger('layers')->default(0);
            $table->unsignedInteger('total_layers')->nullable();
            $table->float('filament_g')->nullable();
            $table->float('filament_mm')->nullable();
            $table->string('slicer')->nullable();
            $table->string('printer')->nullable();
            $table->string('thumbnail')->nullable();
            $table->string('cover')->nullable();
            $table->string('timelapse')->nullable();
            $table->string('video')->nullable();
            $table->unsignedInteger('frames')->default(0);
            $table->float('energy_wh')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('print_jobs');
    }
};
