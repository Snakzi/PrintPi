<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\PrinterBridge;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Mockery\MockInterface;
use Tests\TestCase;

class PrintJobApiTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->actingAs(User::factory()->create());
    }

    public function test_pause_resume_and_cancel_publish_commands(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('pausePrint')->once();
            $mock->shouldReceive('resumePrint')->once();
            $mock->shouldReceive('cancelPrint')->once();
        });

        $this->postJson(route('printer.job.pause'))->assertStatus(202)->assertJsonPath('queued', true);
        $this->postJson(route('printer.job.resume'))->assertStatus(202);
        $this->postJson(route('printer.job.cancel'))->assertStatus(202);
    }

    public function test_restart_publishes_when_the_printer_is_free(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('isConnected')->once()->andReturn(true);
            $mock->shouldReceive('hasActiveJob')->once()->andReturn(false);
            $mock->shouldReceive('restartPrint')->once();
        });

        $this->postJson(route('printer.job.restart'))->assertStatus(202);
    }

    public function test_restart_is_refused_while_a_print_runs(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('isConnected')->once()->andReturn(true);
            $mock->shouldReceive('hasActiveJob')->once()->andReturn(true);
            $mock->shouldNotReceive('restartPrint');
        });

        $this->postJson(route('printer.job.restart'))
            ->assertStatus(409)
            ->assertJsonPath('message', 'A print is already running.');
    }

    public function test_restart_is_refused_without_a_connection(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('isConnected')->once()->andReturn(false);
            $mock->shouldNotReceive('restartPrint');
        });

        $this->postJson(route('printer.job.restart'))
            ->assertStatus(409)
            ->assertJsonPath('message', 'The printer is not connected.');
    }

    public function test_job_routes_require_login(): void
    {
        auth()->logout();

        $this->postJson(route('printer.job.pause'))->assertUnauthorized();
        $this->postJson(route('printer.job.restart'))->assertUnauthorized();
    }
}
