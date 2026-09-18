<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\PrinterBridge;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Process\PendingProcess;
use Illuminate\Support\Facades\Process;
use Mockery\MockInterface;
use Tests\TestCase;

class SystemApiTest extends TestCase
{
    use RefreshDatabase;

    private string $helper;

    protected function setUp(): void
    {
        parent::setUp();
        Process::fake();
        $this->actingAs(User::factory()->create());

        $this->helper = tempnam(sys_get_temp_dir(), 'printpi-system');
        chmod($this->helper, 0755);
        config(['printpi.system_helper' => $this->helper]);
    }

    protected function tearDown(): void
    {
        @unlink($this->helper);
        parent::tearDown();
    }

    public function test_reboot_runs_the_helper(): void
    {
        $this->postJson(route('system.reboot'))
            ->assertAccepted()
            ->assertExactJson(['status' => 'rebooting']);

        Process::assertRan(fn (PendingProcess $process): bool => $process->command === ['sudo', '-n', $this->helper, 'reboot']);
    }

    public function test_restart_web_runs_the_helper(): void
    {
        $this->postJson(route('system.restart-web'))
            ->assertAccepted()
            ->assertExactJson(['status' => 'restarting']);

        Process::assertRan(fn (PendingProcess $process): bool => $process->command === ['sudo', '-n', $this->helper, 'restart-web']);
    }

    public function test_actions_are_refused_without_the_helper(): void
    {
        config(['printpi.system_helper' => sys_get_temp_dir().'/printpi-system-missing']);

        $this->postJson(route('system.reboot'))->assertServiceUnavailable();
        $this->postJson(route('system.restart-web'))->assertServiceUnavailable();
        Process::assertNothingRan();
    }

    public function test_a_failing_helper_is_reported(): void
    {
        Process::fake(fn () => Process::result('', 'sudo: a password is required', 1));

        $this->postJson(route('system.reboot'))
            ->assertInternalServerError()
            ->assertJsonPath('message', 'The reboot could not be started.');
    }

    public function test_session_reports_whether_system_control_is_available(): void
    {
        $this->getJson(route('session.show'))->assertJsonPath('system_control', true);

        config(['printpi.system_helper' => sys_get_temp_dir().'/printpi-system-missing']);
        $this->getJson(route('session.show'))->assertJsonPath('system_control', false);
    }

    public function test_history_returns_the_usage_points(): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('systemHistory')->once()->andReturn([
                'interval' => 30,
                'points' => [[1758000000, 12.5, 41.0], [1758000030, null, 41.2]],
            ]);
        });

        $this->getJson(route('system.history'))
            ->assertOk()
            ->assertJsonPath('interval', 30)
            ->assertJsonPath('points.0.1', 12.5)
            ->assertJsonPath('points.1.1', null)
            ->assertJsonCount(2, 'points');
    }
}
