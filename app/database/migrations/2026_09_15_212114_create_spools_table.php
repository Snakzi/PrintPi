<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('spools', function (Blueprint $table): void {
            $table->id();
            $table->string('name', 100);
            $table->string('vendor', 100)->nullable();
            $table->string('material', 40);
            $table->string('color', 7)->nullable();
            $table->float('diameter')->default(1.75);
            $table->float('density')->default(1.24);
            // Net filament weight when new and the grams consumed since, both in g.
            $table->float('weight')->default(1000);
            $table->float('spool_weight')->nullable();
            $table->float('used')->default(0);
            $table->decimal('price', 8, 2)->nullable();
            $table->boolean('loaded')->default(false);
            $table->timestamp('archived_at')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('spools');
    }
};
