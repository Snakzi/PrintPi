<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('spools', function (Blueprint $table): void {
            // The surface effect of the filament (`glitter`), null for a plain one.
            $table->string('finish', 20)->nullable()->after('color');
        });
    }

    public function down(): void
    {
        Schema::table('spools', function (Blueprint $table): void {
            $table->dropColumn('finish');
        });
    }
};
