<?php

namespace Tests\Feature;

use App\Models\GcodeFile;
use App\Models\PrintJob;
use App\Models\Spool;
use App\Models\User;
use App\Services\PrinterBridge;
use App\Services\Settings;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Storage;
use Mockery\MockInterface;
use Tests\TestCase;

class PrintHistoryApiTest extends TestCase
{
    use RefreshDatabase;

    private const string PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';

    private string $timelapseDir;

    protected function setUp(): void
    {
        parent::setUp();
        $this->actingAs(User::factory()->create());
        Storage::fake('gcode');
        $this->timelapseDir = sys_get_temp_dir().'/printpi-timelapse-'.uniqid();
        mkdir($this->timelapseDir);
        config(['printpi.timelapse_dir' => $this->timelapseDir]);
    }

    protected function tearDown(): void
    {
        File::deleteDirectory($this->timelapseDir);
        parent::tearDown();
    }

    public function test_state_files_the_daemons_records_with_thumbnail_metadata_and_timelapse(): void
    {
        $file = GcodeFile::factory()->create([
            'name' => 'Benchy.gcode',
            'metadata' => ['slicer' => 'PrusaSlicer 2.8.1', 'filament_g' => 12.5, 'filament_mm' => 4000.0],
            'thumbnail' => 'thumbnails/1.png',
        ]);
        Storage::disk('gcode')->put('thumbnails/1.png', base64_decode(self::PNG, true));
        app(Settings::class)->set(['printer_name' => 'Werkstatt MK4S']);
        $this->writeTimelapse('a1b2c3d4e5f6', ['timelapse.gif', 'cover.jpg']);

        $this->mock(PrinterBridge::class, function (MockInterface $mock) use ($file): void {
            $mock->shouldReceive('takeFinishedJobs')->once()->andReturn([$this->record($file->id)]);
            $mock->shouldReceive('takeFilamentEvents')->once()->andReturn([]);
            $mock->shouldReceive('state')->once()->andReturn(['daemon_alive' => true, 'printer' => []]);
        });

        $this->getJson(route('printer.state'))->assertOk();

        $this->assertDatabaseCount('print_jobs', 1);
        $job = PrintJob::query()->firstOrFail();
        $this->assertSame('a1b2c3d4e5f6', $job->key);
        $this->assertSame($file->id, $job->gcode_file_id);
        $this->assertSame('finished', $job->state);
        $this->assertSame(3725, $job->elapsed);
        $this->assertSame(120, $job->layers);
        $this->assertSame(12.5, $job->filament_g);
        $this->assertSame('Werkstatt MK4S', $job->printer);
        $this->assertSame('postcards/a1b2c3d4e5f6.png', $job->thumbnail);
        Storage::disk('gcode')->assertExists('postcards/a1b2c3d4e5f6.png');
        $this->assertSame('a1b2c3d4e5f6/timelapse.gif', $job->timelapse);
        $this->assertSame('a1b2c3d4e5f6/cover.jpg', $job->cover);
        $this->assertNull($job->video);
        $this->assertSame(42.5, $job->energy_wh);
        $this->assertSame('2026-09-15 08:00:00', $job->started_at->toDateTimeString());
    }

    public function test_timestamps_follow_the_configured_timezone(): void
    {
        // AppServiceProvider applies the stored timezone the same way on every request.
        $previous = date_default_timezone_get();
        config(['app.timezone' => 'Europe/Berlin']);
        date_default_timezone_set('Europe/Berlin');
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('takeFinishedJobs')->once()->andReturn([$this->record(null)]);
        });

        try {
            $this->getJson(route('prints.index'))
                ->assertOk()
                ->assertJsonPath('data.0.started_at', '2026-09-15T10:00:00+02:00')
                ->assertJsonPath('data.0.finished_at', '2026-09-15T11:02:05+02:00');
        } finally {
            date_default_timezone_set($previous);
        }
    }

    public function test_index_lists_prints_with_urls_and_files_new_records_first(): void
    {
        $this->writeTimelapse('feedfacecafe', ['timelapse.gif', 'cover.jpg', 'timelapse.mp4']);
        $older = PrintJob::factory()->cancelled()->create(['started_at' => '2026-09-01 10:00:00']);
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('takeFinishedJobs')->twice()->andReturn([$this->record(null, 'feedfacecafe')], []);
        });

        $response = $this->getJson(route('prints.index'))
            ->assertOk()
            ->assertJsonCount(2, 'data')
            ->assertJsonPath('data.0.key', 'feedfacecafe')
            ->assertJsonPath('data.0.state', 'finished')
            ->assertJsonPath('data.0.thumbnail_url', null)
            ->assertJsonPath('data.0.file', null)
            ->assertJsonPath('data.0.filament_g', null)
            ->assertJsonPath('data.0.frames', 7)
            ->assertJsonPath('data.1.key', $older->key)
            ->assertJsonPath('data.1.state', 'cancelled');

        $id = $response->json('data.0.id');
        $this->assertSame("/api/v1/prints/{$id}/timelapse", $response->json('data.0.timelapse_url'));
        $this->assertSame("/api/v1/prints/{$id}/cover", $response->json('data.0.cover_url'));
        $this->assertSame("/api/v1/prints/{$id}/video", $response->json('data.0.video_url'));

        $this->get(route('prints.timelapse', $id))->assertOk()->assertHeader('Content-Type', 'image/gif');
        $this->get(route('prints.cover', $id))->assertOk()->assertHeader('Content-Type', 'image/jpeg');
        $this->get(route('prints.video', $id))->assertOk()->assertHeader('Content-Type', 'video/mp4');
        $this->getJson(route('prints.index', ['key' => 'feedfacecafe']))->assertOk()->assertJsonCount(1, 'data');
        $this->getJson(route('prints.show', $id))->assertOk()->assertJsonPath('data.key', 'feedfacecafe');
    }

    public function test_a_record_is_filed_once_and_the_filament_follows_the_progress(): void
    {
        $file = GcodeFile::factory()->create(['metadata' => ['filament_g' => 10.0, 'filament_mm' => 3000.0]]);
        $record = $this->record($file->id) + [];
        $record['state'] = 'cancelled';
        $record['progress'] = 0.25;
        $record['timelapse'] = null;
        $this->mock(PrinterBridge::class, function (MockInterface $mock) use ($record): void {
            $mock->shouldReceive('takeFinishedJobs')->twice()->andReturn([$record], [$record]);
        });

        $this->getJson(route('prints.index'))->assertOk()->assertJsonCount(1, 'data');
        $this->getJson(route('prints.index'))->assertOk()->assertJsonCount(1, 'data')
            ->assertJsonPath('data.0.state', 'cancelled')
            ->assertJsonPath('data.0.filament_g', 2.5)
            ->assertJsonPath('data.0.filament_mm', 750)
            ->assertJsonPath('data.0.timelapse_url', null)
            ->assertJsonPath('data.0.file.id', $file->id);
    }

    public function test_a_filed_print_is_booked_on_the_loaded_spool(): void
    {
        Spool::factory()->create(['used' => 5]);
        $loaded = Spool::factory()->loaded()->create(['used' => 100, 'price' => 30, 'weight' => 1000]);
        $file = GcodeFile::factory()->create(['metadata' => ['filament_g' => 40.0, 'filament_mm' => 13_000.0]]);
        $record = $this->record($file->id);
        $record['progress'] = 0.5;
        $record['state'] = 'cancelled';
        $this->mock(PrinterBridge::class, function (MockInterface $mock) use ($record): void {
            $mock->shouldReceive('takeFinishedJobs')->once()->andReturn([$record]);
        });

        $this->getJson(route('prints.index'))->assertOk()
            ->assertJsonPath('data.0.filament_g', 20)
            ->assertJsonPath('data.0.spool.id', $loaded->id)
            ->assertJsonPath('data.0.spool.color', $loaded->color)
            ->assertJsonPath('data.0.filament_cost', 0.6);

        $this->assertSame(120.0, $loaded->fresh()->used);
    }

    public function test_a_length_only_file_is_weighed_with_the_spools_density(): void
    {
        $loaded = Spool::factory()->loaded()->create(['used' => 0, 'diameter' => 1.75, 'density' => 1.24]);
        $file = GcodeFile::factory()->create(['metadata' => ['filament_g' => null, 'filament_mm' => 1000.0]]);
        $this->mock(PrinterBridge::class, function (MockInterface $mock) use ($file): void {
            $mock->shouldReceive('takeFinishedJobs')->once()->andReturn([$this->record($file->id)]);
        });

        $this->getJson(route('prints.index'))->assertOk()
            ->assertJsonPath('data.0.filament_g', 2.98)
            ->assertJsonPath('data.0.filament_mm', 1000);

        $this->assertSame(2.98, $loaded->fresh()->used);
    }

    public function test_timelapse_files_outside_the_timelapse_directory_are_ignored(): void
    {
        $record = $this->record(null, 'deadbeef0000');
        $record['timelapse'] = ['gif' => __FILE__, 'cover' => '/nowhere/cover.jpg', 'mp4' => null, 'frames' => 3, 'error' => null];
        $this->mock(PrinterBridge::class, function (MockInterface $mock) use ($record): void {
            $mock->shouldReceive('takeFinishedJobs')->once()->andReturn([$record]);
        });

        $this->getJson(route('prints.index'))->assertOk()
            ->assertJsonPath('data.0.timelapse_url', null)
            ->assertJsonPath('data.0.cover_url', null)
            ->assertJsonPath('data.0.frames', 3);
    }

    public function test_missing_files_answer_404(): void
    {
        $job = PrintJob::factory()->create(['timelapse' => 'gone/timelapse.gif', 'cover' => null, 'thumbnail' => null]);

        $this->get(route('prints.timelapse', $job))->assertNotFound();
        $this->get(route('prints.cover', $job))->assertNotFound();
        $this->get(route('prints.thumbnail', $job))->assertNotFound();
    }

    public function test_destroy_removes_the_row_and_its_files(): void
    {
        $this->writeTimelapse('0123456789ab', ['timelapse.gif', 'cover.jpg']);
        Storage::disk('gcode')->put('postcards/0123456789ab.png', 'png');
        $job = PrintJob::factory()->create([
            'key' => '0123456789ab',
            'thumbnail' => 'postcards/0123456789ab.png',
            'timelapse' => '0123456789ab/timelapse.gif',
            'cover' => '0123456789ab/cover.jpg',
        ]);

        $this->deleteJson(route('prints.destroy', $job))->assertNoContent();

        $this->assertDatabaseMissing('print_jobs', ['id' => $job->id]);
        Storage::disk('gcode')->assertMissing('postcards/0123456789ab.png');
        $this->assertDirectoryDoesNotExist($this->timelapseDir.'/0123456789ab');
    }

    public function test_deleting_the_gcode_file_keeps_the_print(): void
    {
        $file = GcodeFile::factory()->create();
        $job = PrintJob::factory()->create(['gcode_file_id' => $file->id]);

        $file->delete();

        $this->assertNull($job->fresh()->gcode_file_id);
    }

    public function test_prints_require_login(): void
    {
        auth()->logout();

        $this->getJson(route('prints.index'))->assertUnauthorized();
    }

    /**
     * @return array<string, mixed>
     */
    private function record(?int $fileId, string $key = 'a1b2c3d4e5f6'): array
    {
        return [
            'id' => $key,
            'name' => 'Benchy.gcode',
            'path' => '/srv/gcode/Benchy.gcode',
            'file_id' => $fileId,
            'state' => 'finished',
            'error' => null,
            'progress' => 1.0,
            'line' => 5000,
            'total_lines' => 5000,
            'bytes_sent' => 123456,
            'total_bytes' => 123456,
            'layer' => 120,
            'total_layers' => 120,
            'started_at' => 1789459200.0,
            'finished_at' => 1789462925.0,
            'elapsed' => 3725.4,
            'remaining' => 0.0,
            'remaining_source' => null,
            'estimated_seconds' => 3600,
            'energy_wh' => 42.5,
            'timelapse' => [
                'gif' => $this->timelapseDir.'/'.$key.'/timelapse.gif',
                'mp4' => is_file($this->timelapseDir.'/'.$key.'/timelapse.mp4') ? $this->timelapseDir.'/'.$key.'/timelapse.mp4' : null,
                'cover' => $this->timelapseDir.'/'.$key.'/cover.jpg',
                'frames' => 7,
                'error' => null,
            ],
        ];
    }

    /**
     * @param  list<string>  $files
     */
    private function writeTimelapse(string $key, array $files): void
    {
        mkdir($this->timelapseDir.'/'.$key);
        foreach ($files as $name) {
            file_put_contents($this->timelapseDir.'/'.$key.'/'.$name, 'data');
        }
    }

    public function test_the_history_is_pruned_to_the_configured_length_when_a_record_is_filed(): void
    {
        app(Settings::class)->set(['history_keep' => 2]);
        $this->writeTimelapse('0ld0ld0ld0ld', ['timelapse.gif', 'cover.jpg']);
        $oldest = PrintJob::factory()->create(['key' => '0ld0ld0ld0ld', 'timelapse' => '0ld0ld0ld0ld/timelapse.gif', 'cover' => '0ld0ld0ld0ld/cover.jpg']);
        $kept = PrintJob::factory()->create();
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('takeFinishedJobs')->andReturn([$this->record(null, 'feedfacecafe')], []);
        });

        $this->getJson(route('prints.index'))->assertOk()->assertJsonCount(2, 'data')->assertJsonPath('data.0.key', 'feedfacecafe')->assertJsonPath('data.1.key', $kept->key);
        $this->assertDatabaseMissing('print_jobs', ['id' => $oldest->id]);
        $this->assertDirectoryDoesNotExist($this->timelapseDir.'/0ld0ld0ld0ld');

        // Nothing new filed, nothing pruned, even when the table is longer than the limit.
        PrintJob::factory()->count(3)->create();
        $this->getJson(route('prints.index'))->assertOk()->assertJsonCount(5, 'data');
    }
}
