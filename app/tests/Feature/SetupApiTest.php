<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\PrinterBridge;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Process;
use Mockery\MockInterface;
use Tests\TestCase;

class SetupApiTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Process::fake();
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('isDaemonAlive')->andReturn(true);
            $mock->shouldReceive('ports')->andReturn([['device' => '/dev/ttyACM0', 'description' => 'Original Prusa MK4S', 'hwid' => '']]);
            $mock->shouldReceive('cameras')->andReturn([['device' => '/dev/video0', 'name' => 'C270 HD WEBCAM', 'bus' => 'usb-1.3', 'driver' => 'uvcvideo']]);
            $mock->shouldReceive('camera')->andReturn(['running' => false, 'device' => null, 'port' => 8080, 'available' => true, 'error' => null]);
            $mock->shouldReceive('startCamera')->byDefault();
            $mock->shouldReceive('stopCamera')->byDefault();
        });
    }

    /**
     * @return array<string, mixed>
     */
    private function payload(array $overrides = []): array
    {
        return array_merge([
            'username' => 'alice',
            'email' => 'Alice@example.com',
            'password' => 'secret-1234',
            'password_confirmation' => 'secret-1234',
            'hostname' => 'printpi',
            'timezone' => 'Europe/Berlin',
            'printer_profile' => 'prusa-mk4s',
            'printer_name' => 'MK4S in the office',
            'serial_port' => '/dev/ttyACM0',
            'baud_rate' => 115200,
            'camera_device' => '/dev/video0',
            'camera_url' => null,
        ], $overrides);
    }

    public function test_show_lists_everything_the_wizard_needs(): void
    {
        $this->getJson(route('setup.show'))
            ->assertOk()
            ->assertJsonPath('daemon_alive', true)
            ->assertJsonPath('ports.0.device', '/dev/ttyACM0')
            ->assertJsonPath('cameras.0.name', 'C270 HD WEBCAM')
            ->assertJsonPath('stream_url', '/webcam/stream')
            ->assertJsonPath('system_control', false)
            ->assertJsonStructure(['hostname', 'timezone', 'printers' => [['id', 'manufacturer', 'model', 'type', 'bed', 'baud_rate', 'supported']]]);
    }

    public function test_store_creates_the_admin_saves_settings_and_logs_in(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('startCamera')->once()->with('/dev/video0');
        });

        $this->postJson(route('setup.store'), $this->payload())
            ->assertCreated()
            ->assertJsonPath('user.username', 'alice')
            ->assertJsonPath('user.email', 'alice@example.com')
            ->assertJsonPath('settings.printer_profile', 'prusa-mk4s')
            ->assertJsonPath('settings.camera_device', '/dev/video0')
            ->assertJsonPath('hostname_applied', false);

        $this->assertDatabaseHas('users', ['username' => 'alice']);
        $this->assertSame(32, strlen((string) User::query()->sole()->api_key));
        $this->assertAuthenticated();
        $this->getJson(route('settings.show'))->assertJsonPath('hostname', 'printpi')->assertJsonPath('timezone', 'Europe/Berlin');
    }

    public function test_store_applies_hostname_and_timezone_through_the_helper(): void
    {
        $helper = tempnam(sys_get_temp_dir(), 'printpi-system');
        chmod($helper, 0755);
        config(['printpi.system_helper' => $helper]);

        $this->postJson(route('setup.store'), $this->payload(['camera_device' => null]))
            ->assertCreated()
            ->assertJsonPath('hostname_applied', true)
            ->assertJsonPath('timezone_applied', true);

        Process::assertRan(fn ($process) => $process->command === ['sudo', '-n', $helper, 'set-hostname', 'printpi']);
        Process::assertRan(fn ($process) => $process->command === ['sudo', '-n', $helper, 'set-timezone', 'Europe/Berlin']);
        unlink($helper);
    }

    public function test_setup_is_closed_once_a_user_exists(): void
    {
        User::factory()->create();

        $this->getJson(route('setup.show'))->assertForbidden();
        $this->postJson(route('setup.store'), $this->payload())->assertForbidden();
        $this->assertDatabaseCount('users', 1);
    }

    public function test_store_validates_input(): void
    {
        $this->postJson(route('setup.store'), $this->payload([
            'email' => 'not-an-address',
            'password_confirmation' => 'different',
            'hostname' => 'My Pi!',
            'printer_profile' => 'klipper',
            'timezone' => 'Mars/Olympus',
            'camera_device' => '/etc/passwd',
        ]))
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['email', 'password', 'hostname', 'printer_profile', 'timezone', 'camera_device']);

        $this->assertDatabaseCount('users', 0);
    }

    public function test_store_returns_422_without_a_baud_rate(): void
    {
        $payload = $this->payload();
        unset($payload['baud_rate']);

        $this->postJson(route('setup.store'), $payload)
            ->assertUnprocessable()
            ->assertJsonValidationErrors('baud_rate');

        $this->assertDatabaseCount('users', 0);
    }
}
