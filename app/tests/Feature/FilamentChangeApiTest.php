<?php

namespace Tests\Feature;

use App\Models\Setting;
use App\Models\Spool;
use App\Models\User;
use App\Services\FilamentChange;
use App\Services\PrinterBridge;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Mockery\MockInterface;
use Tests\TestCase;

class FilamentChangeApiTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->actingAs(User::factory()->create());
    }

    public function test_load_hands_the_spool_its_temperature_and_the_profiles_moves_to_the_daemon(): void
    {
        Setting::query()->create(['key' => 'printer_profile', 'value' => 'prusa-mk4s']);
        $spool = Spool::factory()->create(['name' => 'Galaxy Black', 'material' => 'PETG', 'color' => '#26262e']);

        $this->mock(PrinterBridge::class, function (MockInterface $mock) use ($spool): void {
            $this->free($mock);
            $mock->shouldReceive('startFilament')->once()->withArgs(function (string $action, ?array $summary, ?string $material, ?int $nozzle, ?int $unloadNozzle, ?array $moves) use ($spool): bool {
                return $action === 'load'
                    && $summary === ['id' => $spool->id, 'name' => 'Galaxy Black', 'material' => 'PETG', 'color' => '#26262e']
                    && $material === 'PETG' && $nozzle === 230 && $unloadNozzle === null
                    && $moves['purge'] === [27, 162] && $moves['load'] === [[30, 324], [50, 1080]]
                    && array_sum(array_column($moves['unload'], 0)) === -97;
            });
        });

        $this->postJson(route('printer.filament.load'), ['spool_id' => $spool->id])->assertStatus(202)->assertJsonPath('queued', true);
    }

    public function test_load_with_unload_first_is_a_change_at_the_loaded_spools_temperature(): void
    {
        Spool::factory()->create(['material' => 'ASA', 'loaded' => true]);
        $spool = Spool::factory()->create(['material' => 'PLA']);

        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $this->free($mock);
            $mock->shouldReceive('startFilament')->once()->withArgs(fn (string $action, ?array $summary, ?string $material, ?int $nozzle, ?int $unloadNozzle): bool => $action === 'change' && $nozzle === 215 && $unloadNozzle === 260);
        });

        $this->postJson(route('printer.filament.load'), ['spool_id' => $spool->id, 'unload_first' => true])->assertStatus(202);
    }

    public function test_load_by_material_alone_guesses_the_temperature_from_the_name(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $this->free($mock);
            $mock->shouldReceive('startFilament')->once()->withArgs(fn (string $action, ?array $summary, ?string $material, ?int $nozzle, ?int $unloadNozzle, ?array $moves): bool => $action === 'change' && $summary === null && $material === 'PLA Silk' && $nozzle === 215 && $unloadNozzle === 230 && $moves === null);
        });

        $this->postJson(route('printer.filament.load'), ['material' => 'PLA Silk', 'unload_first' => true])->assertStatus(202);
    }

    public function test_load_needs_a_spool_or_a_material(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldNotReceive('startFilament');
        });

        $this->postJson(route('printer.filament.load'), [])->assertUnprocessable()->assertJsonValidationErrors(['spool_id', 'material']);
        $this->postJson(route('printer.filament.load'), ['spool_id' => 999])->assertUnprocessable()->assertJsonValidationErrors(['spool_id']);
    }

    public function test_unload_uses_the_loaded_spools_material(): void
    {
        Spool::factory()->create(['material' => 'PC', 'loaded' => true]);

        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $this->free($mock);
            $mock->shouldReceive('startFilament')->once()->withArgs(fn (string $action, ?array $summary, ?string $material, ?int $nozzle, ?int $unloadNozzle): bool => $action === 'unload' && $material === 'PC' && $nozzle === null && $unloadNozzle === 275);
        });

        $this->postJson(route('printer.filament.unload'))->assertStatus(202);
    }

    public function test_unload_without_a_loaded_spool_heats_enough_for_the_usual_materials(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $this->free($mock);
            $mock->shouldReceive('startFilament')->once()->withArgs(fn (string $action, ?array $summary, ?string $material, ?int $nozzle, ?int $unloadNozzle): bool => $action === 'unload' && $material === null && $unloadNozzle === FilamentChange::UNKNOWN_UNLOAD_NOZZLE);
        });

        $this->postJson(route('printer.filament.unload'))->assertStatus(202);
    }

    public function test_a_walkthrough_is_refused_while_the_printer_is_busy(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('isConnected')->andReturn(false, true, true);
            $mock->shouldReceive('hasActiveJob')->andReturn(true, false);
            $mock->shouldReceive('hasActiveFilament')->andReturn(true);
            $mock->shouldNotReceive('startFilament');
        });

        $this->postJson(route('printer.filament.unload'))->assertStatus(409)->assertJsonPath('message', 'The printer is not connected.');
        $this->postJson(route('printer.filament.unload'))->assertStatus(409)->assertJsonPath('message', 'A print is running.');
        $this->postJson(route('printer.filament.unload'))->assertStatus(409)->assertJsonPath('message', 'A filament change is already running.');
    }

    public function test_continue_answer_and_cancel_reach_the_daemon_while_a_walkthrough_runs(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('hasActiveFilament')->andReturn(true);
            $mock->shouldReceive('activeFilament')->andReturn(['backend' => 'host', 'step' => 'check']);
            $mock->shouldReceive('continueFilament')->once();
            $mock->shouldReceive('answerFilament')->once()->with('purge');
            $mock->shouldReceive('cancelFilament')->once();
        });

        $this->postJson(route('printer.filament.continue'))->assertStatus(202);
        $this->postJson(route('printer.filament.answer'), ['answer' => 'purge'])->assertStatus(202);
        $this->postJson(route('printer.filament.answer'), ['answer' => 'later'])->assertUnprocessable();
        $this->postJson(route('printer.filament.cancel'))->assertStatus(202);
    }

    public function test_continue_is_refused_without_a_walkthrough(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('hasActiveFilament')->once()->andReturn(false);
            $mock->shouldNotReceive('continueFilament');
        });

        $this->postJson(route('printer.filament.continue'))->assertStatus(409)->assertJsonPath('message', 'No filament change is running.');
    }

    public function test_native_display_questions_cannot_be_answered_or_cancelled_from_the_app(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('hasActiveFilament')->andReturn(true);
            $mock->shouldReceive('activeFilament')->andReturn(['backend' => 'firmware', 'step' => 'printer_load', 'waiting' => false]);
            $mock->shouldNotReceive('continueFilament');
            $mock->shouldNotReceive('answerFilament');
            $mock->shouldNotReceive('cancelFilament');
        });

        foreach (['continue', 'answer', 'cancel'] as $action) {
            $this->postJson(route('printer.filament.'.$action), ['answer' => 'yes'])
                ->assertStatus(409)
                ->assertJsonPath('message', 'Follow the instructions on the printer display. Stop the operation there if needed.');
        }
    }

    public function test_the_native_result_can_be_confirmed_or_rejected_after_the_display_dialog_ends(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('hasActiveFilament')->andReturn(true);
            $mock->shouldReceive('activeFilament')->andReturn(['backend' => 'firmware', 'step' => 'confirm_loaded', 'waiting' => true]);
            $mock->shouldReceive('continueFilament')->once();
            $mock->shouldReceive('cancelFilament')->once();
        });

        $this->postJson(route('printer.filament.continue'))->assertStatus(202)->assertJsonPath('queued', true);
        $this->postJson(route('printer.filament.cancel'))->assertStatus(202)->assertJsonPath('queued', true);
    }

    public function test_the_state_poll_books_what_the_walkthrough_loaded_and_unloaded(): void
    {
        $old = Spool::factory()->create(['loaded' => true]);
        $new = Spool::factory()->create();

        $this->mock(PrinterBridge::class, function (MockInterface $mock) use ($new): void {
            $mock->shouldReceive('takeFinishedJobs')->andReturn([]);
            $mock->shouldReceive('state')->andReturn(['daemon_alive' => true, 'printer' => []]);
            $mock->shouldReceive('takeFilamentEvents')->andReturn(
                [['event' => 'unloaded', 'spool' => null, 'at' => 1.0]],
                [['event' => 'loaded', 'spool' => ['id' => $new->id, 'name' => $new->name], 'at' => 2.0]],
                [['event' => 'loaded', 'spool' => null, 'at' => 3.0]],
            );
        });

        $this->getJson(route('printer.state'))->assertOk();
        $this->assertFalse($old->fresh()->loaded);
        $this->assertFalse($new->fresh()->loaded);

        $this->getJson(route('printer.state'))->assertOk();
        $this->assertTrue($new->fresh()->loaded);
        $this->assertFalse($old->fresh()->loaded);

        $this->getJson(route('printer.state'))->assertOk();
        $this->assertFalse($new->fresh()->loaded, 'filament without a spool leaves nothing loaded');
    }

    public function test_the_nozzle_temperature_follows_the_catalog_and_its_prefixes(): void
    {
        $this->assertSame(215, FilamentChange::nozzleFor('PLA'));
        $this->assertSame(250, FilamentChange::nozzleFor('petg-cf'));
        $this->assertSame(230, FilamentChange::nozzleFor('PETG Carbon'));
        $this->assertSame(220, FilamentChange::nozzleFor('Wood'));
        $this->assertSame(220, FilamentChange::nozzleFor(null));
        $this->assertTrue(FilamentChange::knowsMaterial('PLA Silk'));
        $this->assertFalse(FilamentChange::knowsMaterial('Wood'));
    }

    private function free(MockInterface $mock): void
    {
        $mock->shouldReceive('isConnected')->once()->andReturn(true);
        $mock->shouldReceive('hasActiveJob')->once()->andReturn(false);
        $mock->shouldReceive('hasActiveFilament')->once()->andReturn(false);
    }
}
