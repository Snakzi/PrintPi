<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\PrinterBridge;
use App\Services\Settings;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Mockery\MockInterface;
use Tests\TestCase;

class PrinterApiTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->actingAs(User::factory()->create());
    }

    public function test_state_returns_daemon_and_printer_state(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('takeFinishedJobs')->once()->andReturn([]);
            $mock->shouldReceive('takeFilamentEvents')->once()->andReturn([]);
            $mock->shouldReceive('state')->once()->andReturn([
                'daemon_alive' => true,
                'printer' => ['connection' => 'connected', 'temperatures' => ['T0' => ['actual' => 21.5, 'target' => 0.0]]],
            ]);
        });

        $this->getJson(route('printer.state'))
            ->assertOk()
            ->assertJsonPath('daemon_alive', true)
            ->assertJsonPath('printer.connection', 'connected')
            ->assertJsonPath('printer.temperatures.T0.actual', 21.5);
    }

    public function test_serial_returns_lines_with_clamped_limit(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('serialLog')->once()->with(500)->andReturn([
                ['dir' => 'tx', 'line' => 'N1 G28*18', 't' => 1.0],
                ['dir' => 'rx', 'line' => 'ok', 't' => 2.0],
            ]);
        });

        $this->getJson(route('printer.serial', ['limit' => 9999]))
            ->assertOk()
            ->assertJsonCount(2, 'lines')
            ->assertJsonPath('lines.1.line', 'ok');
    }

    public function test_command_publishes_gcode(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('sendGcode')->once()->with('G28');
        });

        $this->postJson(route('printer.command'), ['command' => 'G28'])
            ->assertStatus(202)
            ->assertJsonPath('queued', true);
    }

    public function test_command_rejects_multiline_and_empty_input(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldNotReceive('sendGcode');
        });

        $this->postJson(route('printer.command'), ['command' => "G28\nM112"])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('command');

        $this->postJson(route('printer.command'), [])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('command');
    }

    public function test_connect_publishes_port_and_remembers_it(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('connect')->once()->with('/dev/ttyACM0', 250000);
        });

        $this->postJson(route('printer.connect'), ['port' => '/dev/ttyACM0', 'baud' => 250000])->assertStatus(202);

        $this->getJson(route('settings.show'))
            ->assertJsonPath('serial_port', '/dev/ttyACM0')
            ->assertJsonPath('baud_rate', 250000);
    }

    public function test_reconnect_publishes_the_stored_port(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('connect')->once()->with('/dev/ttyACM0', 250000);
        });
        app(Settings::class)->set(['serial_port' => '/dev/ttyACM0', 'baud_rate' => 250000]);

        $this->postJson(route('printer.reconnect'))->assertStatus(202)->assertJsonPath('queued', true);
    }

    public function test_reconnect_needs_a_previously_connected_port(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldNotReceive('connect');
        });

        $this->postJson(route('printer.reconnect'))->assertStatus(409);
    }

    public function test_connect_requires_a_port_and_a_known_baud_rate(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldNotReceive('connect');
        });

        $this->postJson(route('printer.connect'), ['baud' => 123])
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['port', 'baud']);
    }

    public function test_disconnect_and_emergency_stop_endpoints(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('disconnect')->once();
            $mock->shouldReceive('emergencyStop')->once();
        });

        $this->postJson(route('printer.disconnect'))->assertStatus(202);
        $this->postJson(route('printer.emergency-stop'))->assertStatus(202);
    }
}
