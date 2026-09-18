<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\PrinterBridge;
use App\Services\Settings;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Mockery\MockInterface;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

class CameraApiTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->actingAs(User::factory()->create());
    }

    public function test_show_returns_cameras_status_and_urls(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('cameras')->once()->andReturn([['device' => '/dev/video0', 'name' => 'C270', 'bus' => 'usb-1.3', 'driver' => 'uvcvideo']]);
            $mock->shouldReceive('camera')->once()->andReturn(['running' => true, 'device' => '/dev/video0', 'port' => 8080, 'available' => true, 'error' => null]);
        });
        app(Settings::class)->set(['camera_device' => '/dev/video0']);

        $this->getJson(route('camera.show'))
            ->assertOk()
            ->assertJsonPath('cameras.0.device', '/dev/video0')
            ->assertJsonPath('status.running', true)
            ->assertJsonPath('stream_url', '/webcam/stream')
            ->assertJsonPath('snapshot_url', '/webcam/snapshot')
            ->assertJsonPath('settings.camera_device', '/dev/video0');
    }

    public function test_start_uses_the_given_or_configured_device(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('startCamera')->once()->with('/dev/video2');
            $mock->shouldReceive('startCamera')->once()->with('/dev/video0');
        });

        $this->postJson(route('camera.start'), ['device' => '/dev/video2'])->assertStatus(202);

        app(Settings::class)->set(['camera_device' => '/dev/video0']);
        $this->postJson(route('camera.start'))->assertStatus(202)->assertJsonPath('device', '/dev/video0');
    }

    public function test_start_without_any_camera_is_rejected(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldNotReceive('startCamera');
        });

        $this->postJson(route('camera.start'))->assertUnprocessable();
        $this->postJson(route('camera.start'), ['device' => '/etc/passwd'])->assertUnprocessable();
    }

    public function test_stop_publishes(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('stopCamera')->once();
        });

        $this->postJson(route('camera.stop'))->assertStatus(202);
    }

    #[DataProvider('invalidCameraDevices')]
    public function test_camera_start_returns_422_for_devices_outside_the_allowlist(string $device): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldNotReceive('startCamera');
        });

        $this->postJson(route('camera.start'), ['device' => $device])
            ->assertUnprocessable()->assertJsonValidationErrors('device');
    }

    /** @return array<string, array{string}> */
    public static function invalidCameraDevices(): array
    {
        return [
            'USB suffix' => ['/dev/video0/other'],
            'stream URL' => ['http://camera.local/stream'],
            'other device' => ['/dev/ttyACM0'],
        ];
    }
}
