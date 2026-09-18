<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\PrinterBridge;
use App\Services\Settings;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Request;
use Illuminate\Process\PendingProcess;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Process;
use Illuminate\Support\Facades\Storage;
use Mockery\MockInterface;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;
use Throwable;

class UpdateApiTest extends TestCase
{
    use RefreshDatabase;

    private string $home;

    private string $helper;

    private string $versionFile;

    private string $statusFile;

    protected function setUp(): void
    {
        parent::setUp();
        $this->actingAs(User::factory()->create());
        Process::fake();
        Http::preventStrayRequests();
        Storage::fake('gcode');
        $this->mock(PrinterBridge::class);

        $this->home = tempnam(sys_get_temp_dir(), 'printpi-updates');
        unlink($this->home);
        mkdir($this->home);
        $this->helper = $this->home.'/printpi-system';
        $this->versionFile = $this->home.'/VERSION';
        $this->statusFile = $this->home.'/update.json';
        file_put_contents($this->helper, "#!/bin/sh\n");
        chmod($this->helper, 0755);
        file_put_contents($this->versionFile, "0.1.0\n");
        config([
            'printpi.home' => $this->home,
            'printpi.system_helper' => $this->helper,
            'printpi.version_file' => $this->versionFile,
            'printpi.update_status_file' => $this->statusFile,
            'printpi.update_url' => 'https://updates.example.test',
            'printpi.update_channels' => ['stable', 'beta'],
            'app.timezone' => 'Europe/Berlin',
        ]);
    }

    protected function tearDown(): void
    {
        File::deleteDirectory($this->home);
        parent::tearDown();
    }

    public function test_show_reports_installed_version_and_newest_newer_release_with_exact_contract(): void
    {
        $this->travelTo(CarbonImmutable::parse('2026-09-15T16:00:00Z'));
        $release = [
            'version' => '0.10.0',
            'date' => '2026-09-15',
            'notes' => 'Release notes text',
            'size' => 12345678,
            'sha256' => str_repeat('a', 64),
            'url' => 'https://updates.example.test/stable/printpi-0.10.0.tar.gz',
        ];
        $this->fakeManifest([
            ['version' => '0.2.0'],
            $release + ['min_version' => '0.1.0', 'extra' => 'not exposed'],
            ['version' => '0.9.0'],
            ['version' => 123],
            ['notes' => 'Missing version'],
            'invalid entry',
        ]);

        $this->getJson(route('system.update.show'))->assertOk()->assertExactJson([
            'installed' => '0.1.0',
            'channel' => 'stable',
            'channels' => ['stable', 'beta'],
            'update_url' => 'https://updates.example.test',
            'available' => $release,
            'checked_at' => '2026-09-15T18:00:00+02:00',
            'error' => null,
            'status' => null,
            'previous' => null,
            'system_control' => true,
        ]);

        Http::assertSent(fn (Request $request): bool => $request->method() === 'GET'
            && $request->url() === 'https://updates.example.test/stable/releases.json'
            && $request->hasHeader('Accept', 'application/json'));
        Http::assertSentCount(1);
    }

    public function test_show_has_no_update_for_older_or_equal_releases(): void
    {
        $this->fakeManifest([['version' => '0.0.9'], ['version' => '0.1.0']]);

        $this->getJson(route('system.update.show'))->assertOk()->assertJsonPath('available', null);
    }

    public function test_minimum_version_hides_incompatible_releases(): void
    {
        $this->fakeManifest([
            ['version' => '0.3.0', 'min_version' => '0.2.0'],
            ['version' => '0.2.0', 'min_version' => '0.1.0'],
        ]);

        $this->getJson(route('system.update.show'))->assertOk()->assertJsonPath('available', [
            'version' => '0.2.0', 'date' => null, 'notes' => null, 'size' => null, 'sha256' => null, 'url' => null,
        ]);
    }

    public function test_missing_version_file_reports_dev_and_compares_as_zero(): void
    {
        unlink($this->versionFile);
        $this->fakeManifest([
            ['version' => '0.0.0'],
            ['version' => '0.1.0', 'min_version' => '0.0.0'],
            ['version' => '0.2.0', 'min_version' => '0.1.0'],
        ]);

        $this->getJson(route('system.update.show'))->assertOk()
            ->assertJsonPath('installed', 'dev')->assertJsonPath('available.version', '0.1.0');
    }

    public function test_manifest_is_cached_for_a_day_and_check_forces_a_refresh(): void
    {
        $this->travelTo(CarbonImmutable::parse('2026-09-15T16:00:00Z'));
        Http::fake(['https://updates.example.test/stable/releases.json' => Http::sequence()
            ->push(['releases' => [['version' => '0.2.0']]])
            ->push(['releases' => [['version' => '0.3.0']]])
            ->push(['releases' => [['version' => '0.4.0']]])]);

        $this->getJson(route('system.update.show'))->assertJsonPath('available.version', '0.2.0');
        $this->travel(23)->hours();
        $this->getJson(route('system.update.show'))->assertJsonPath('available.version', '0.2.0');
        Http::assertSentCount(1);

        $this->getJson(route('system.update.show', ['check' => 1]))
            ->assertJsonPath('available.version', '0.3.0')
            ->assertJsonPath('checked_at', '2026-09-16T17:00:00+02:00');
        $this->getJson(route('system.update.show'))->assertJsonPath('available.version', '0.3.0');
        Http::assertSentCount(2);

        $this->travel(25)->hours();
        $this->getJson(route('system.update.show'))->assertJsonPath('available.version', '0.4.0');
        Http::assertSentCount(3);
    }

    public function test_unreachable_server_keeps_cached_release_and_last_successful_check_time(): void
    {
        $this->travelTo(CarbonImmutable::parse('2026-09-15T16:00:00Z'));
        $this->fakeManifest([['version' => '0.2.0']]);
        $this->getJson(route('system.update.show'))->assertOk();
        $this->travel(1)->hour();
        Http::fake(['https://updates.example.test/stable/releases.json' => Http::failedConnection('Private connection details')]);
        Log::shouldReceive('warning')->once()->with('The update manifest could not be fetched.',
            \Mockery::on(fn (array $context): bool => $context['exception'] instanceof Throwable));

        $this->getJson(route('system.update.show', ['check' => 1]))->assertOk()
            ->assertJsonPath('available.version', '0.2.0')
            ->assertJsonPath('checked_at', '2026-09-15T18:00:00+02:00')
            ->assertJsonPath('error', 'The update server could not be reached.');

        $this->getJson(route('system.update.show'))->assertJsonPath('available.version', '0.2.0');
    }

    public function test_unreachable_server_without_cache_reports_no_available_release_or_check_time(): void
    {
        Http::fake(['https://updates.example.test/stable/releases.json' => Http::failedConnection()]);

        $this->getJson(route('system.update.show'))->assertOk()
            ->assertJsonPath('available', null)->assertJsonPath('checked_at', null)
            ->assertJsonPath('error', 'The update server could not be reached.');
    }

    #[DataProvider('invalidManifests')]
    public function test_invalid_manifest_or_http_failure_keeps_cached_releases(string $body, int $status): void
    {
        Http::fake(['https://updates.example.test/stable/releases.json' => Http::sequence()
            ->push(['releases' => [['version' => '0.2.0']]])->push($body, $status)]);
        $this->getJson(route('system.update.show'))->assertOk();

        $this->getJson(route('system.update.show', ['check' => 1]))->assertOk()
            ->assertJsonPath('available.version', '0.2.0')
            ->assertJsonPath('error', 'The update server could not be reached.');
        Http::assertSentCount(2);
    }

    /** @return array<string, array{string, int}> */
    public static function invalidManifests(): array
    {
        return [
            'missing releases' => ['{"latest":"0.3.0"}', 200],
            'object releases' => ['{"releases":{}}', 200],
            'null releases' => ['{"releases":null}', 200],
            'invalid json' => ['{', 200],
            'http failure' => ['{"releases":[]}', 503],
        ];
    }

    public function test_channels_have_separate_manifest_caches(): void
    {
        $this->fakeManifest([['version' => '0.2.0']]);
        $this->fakeManifest([['version' => '0.3.0-beta.1']], 'beta');
        $this->getJson(route('system.update.show'))->assertJsonPath('available.version', '0.2.0');
        app(Settings::class)->set(['update_channel' => 'beta']);

        $this->getJson(route('system.update.show'))->assertOk()
            ->assertJsonPath('channel', 'beta')->assertJsonPath('available.version', '0.3.0-beta.1');
        app(Settings::class)->set(['update_channel' => 'stable']);
        $this->getJson(route('system.update.show'))->assertJsonPath('available.version', '0.2.0');
        Http::assertSentCount(2);
    }

    public function test_status_is_passed_through_including_a_failed_updates_error(): void
    {
        $this->fakeManifest([]);
        $status = [
            'action' => 'update', 'version' => '0.2.0', 'phase' => 'downloading', 'step' => null,
            'started_at' => '2026-09-15T18:00:00Z', 'finished_at' => null, 'error' => null,
        ];
        file_put_contents($this->statusFile, json_encode($status));
        $this->getJson(route('system.update.show'))->assertOk()->assertJsonPath('status', $status);

        $status['phase'] = 'installing';
        $status['step'] = 'Migrating the database';
        file_put_contents($this->statusFile, json_encode($status));
        $this->getJson(route('system.update.show'))->assertOk()->assertJsonPath('status', $status);

        $status['phase'] = 'failed';
        $status['step'] = null;
        $status['finished_at'] = '2026-09-15T18:01:00Z';
        $status['error'] = 'The release signature is invalid.';
        file_put_contents($this->statusFile, json_encode($status));
        $this->getJson(route('system.update.show'))->assertOk()->assertJsonPath('status', $status);
    }

    #[DataProvider('invalidStatuses')]
    public function test_invalid_status_is_reported_as_null(string $contents): void
    {
        $this->fakeManifest([]);
        file_put_contents($this->statusFile, $contents);

        $this->getJson(route('system.update.show'))->assertOk()->assertJsonPath('status', null);
    }

    /** @return array<string, array{string}> */
    public static function invalidStatuses(): array
    {
        return ['broken json' => ['{'], 'scalar' => ['42'], 'null' => ['null'], 'array' => ['[]']];
    }

    public function test_start_runs_the_helper_with_the_cached_version_and_channel_from_settings(): void
    {
        app(Settings::class)->set(['update_channel' => 'beta']);
        $this->fakeManifest([['version' => '0.2.0-beta.1']], 'beta');
        $this->printerState('idle');
        $this->getJson(route('system.update.show'))->assertOk();

        $this->postJson(route('system.update.start'), ['version' => '0.2.0-beta.1', 'channel' => 'stable'])
            ->assertAccepted()->assertExactJson(['status' => 'updating', 'version' => '0.2.0-beta.1']);

        Process::assertRan(fn (PendingProcess $process): bool => $process->command === [
            'sudo', '-n', $this->helper, 'update', '0.2.0-beta.1', 'beta',
        ]);
        Http::assertSentCount(1);
    }

    #[DataProvider('activePrintStates')]
    public function test_actions_return_409_while_a_print_is_active(string $state): void
    {
        $this->printerState($state);

        $this->postJson(route('system.update.start'), ['version' => '0.2.0'])->assertConflict()
            ->assertJsonPath('message', 'A print is running.');
        $this->postJson(route('system.update.rollback'))->assertConflict()
            ->assertJsonPath('message', 'A print is running.');

        Http::assertNothingSent();
        Process::assertNothingRan();
    }

    /** @return array<string, array{string}> */
    public static function activePrintStates(): array
    {
        return ['printing' => ['printing'], 'paused' => ['paused'], 'cancelling' => ['cancelling']];
    }

    #[DataProvider('activeUpdatePhases')]
    public function test_actions_return_409_while_an_update_is_in_progress(string $phase): void
    {
        file_put_contents($this->statusFile, json_encode(['action' => 'rollback', 'phase' => $phase]));

        $this->postJson(route('system.update.start'), ['version' => '0.2.0'])->assertConflict()
            ->assertJsonPath('message', 'An update is already running.');
        $this->postJson(route('system.update.rollback'))->assertConflict()
            ->assertJsonPath('message', 'An update is already running.');

        Http::assertNothingSent();
        Process::assertNothingRan();
    }

    /** @return array<string, array{string}> */
    public static function activeUpdatePhases(): array
    {
        return [
            'queued' => ['queued'], 'downloading' => ['downloading'], 'verifying' => ['verifying'],
            'unpacking' => ['unpacking'], 'installing' => ['installing'], 'switching' => ['switching'],
        ];
    }

    public function test_unknown_version_returns_422(): void
    {
        $this->printerState('idle');
        $this->fakeManifest([['version' => '0.2.0']]);

        $this->postJson(route('system.update.start'), ['version' => '9.9.9'])->assertUnprocessable()
            ->assertJsonValidationErrors(['version' => 'This version is not available.']);
        Process::assertNothingRan();
    }

    #[DataProvider('invalidVersions')]
    public function test_invalid_version_returns_422_without_running_the_helper(array $payload): void
    {
        $this->postJson(route('system.update.start'), $payload)->assertUnprocessable()
            ->assertJsonValidationErrors('version');

        Http::assertNothingSent();
        Process::assertNothingRan();
    }

    /** @return array<string, array{array<string, mixed>}> */
    public static function invalidVersions(): array
    {
        return [
            'missing' => [[]],
            'not a string' => [['version' => 123]],
            'shell syntax' => [['version' => '0.2.0; reboot']],
            'incomplete version' => [['version' => '0.2']],
            'build metadata' => [['version' => '0.2.0+build']],
        ];
    }

    public function test_actions_return_503_without_the_helper_and_show_reports_it_unavailable(): void
    {
        config(['printpi.system_helper' => $this->home.'/missing']);
        file_put_contents($this->statusFile, '{"phase":"installing"}');
        $this->fakeManifest([]);

        $this->postJson(route('system.update.start'), ['version' => '0.2.0'])->assertServiceUnavailable()
            ->assertJsonPath('message', 'System control is not available on this host.');
        $this->postJson(route('system.update.rollback'))->assertServiceUnavailable()
            ->assertJsonPath('message', 'System control is not available on this host.');
        $this->getJson(route('system.update.show'))->assertOk()->assertJsonPath('system_control', false);

        Process::assertNothingRan();
    }

    public function test_rollback_runs_the_helper_and_reports_the_previous_version(): void
    {
        $this->printerState('idle');
        $this->previousRelease();
        $this->fakeManifest([]);
        $this->getJson(route('system.update.show'))->assertJsonPath('previous', '0.0.9');

        $this->postJson(route('system.update.rollback'))->assertAccepted()
            ->assertExactJson(['status' => 'rolling_back', 'version' => '0.0.9']);

        Process::assertRan(fn (PendingProcess $process): bool => $process->command === ['sudo', '-n', $this->helper, 'rollback']);
    }

    public function test_previous_version_falls_back_to_the_relative_symlink_target_name(): void
    {
        $this->printerState('idle');
        mkdir($this->home.'/0.0.8');
        symlink('0.0.8', $this->home.'/previous');

        $this->postJson(route('system.update.rollback'))->assertAccepted()
            ->assertExactJson(['status' => 'rolling_back', 'version' => '0.0.8']);
    }

    public function test_rollback_returns_409_without_a_previous_symlink(): void
    {
        $this->printerState('idle');
        mkdir($this->home.'/previous');
        file_put_contents($this->home.'/previous/VERSION', '0.0.9');

        $this->postJson(route('system.update.rollback'))->assertConflict()
            ->assertJsonPath('message', 'Nothing to roll back to.');
        Process::assertNothingRan();
    }

    public function test_completed_or_failed_updates_do_not_block_actions_and_helper_refusals_return_500_with_the_reason(): void
    {
        $this->printerState('idle');
        $this->previousRelease();
        $this->fakeManifest([['version' => '0.2.0']]);
        Process::fake(fn () => Process::result('', "a print job is active\n", 4));
        file_put_contents($this->statusFile, '{"phase":"done"}');

        $this->postJson(route('system.update.start'), ['version' => '0.2.0'])->assertInternalServerError()
            ->assertJsonPath('message', 'A print job is active.');
        file_put_contents($this->statusFile, '{"phase":"failed","error":"The last update failed."}');
        Process::fake(fn () => Process::result('', '', 1));
        $this->postJson(route('system.update.rollback'))->assertInternalServerError()
            ->assertJsonPath('message', 'The rollback could not be started.');
        Process::assertRanTimes(fn (PendingProcess $process): bool => $process->command === [
            'sudo', '-n', $this->helper, 'update', '0.2.0', 'stable',
        ]);
        Process::assertRanTimes(['sudo', '-n', $this->helper, 'rollback']);
    }

    public function test_a_stored_channel_the_host_does_not_publish_falls_back_to_the_first_published_one(): void
    {
        config(['printpi.update_channels' => ['beta']]);
        app(Settings::class)->set(['update_channel' => 'stable']);
        $this->fakeManifest([['version' => '0.2.0-beta.1']], 'beta');
        $this->printerState('idle');

        $this->getJson(route('system.update.show'))->assertOk()
            ->assertJsonPath('channel', 'beta')->assertJsonPath('channels', ['beta'])
            ->assertJsonPath('available.version', '0.2.0-beta.1');
        $this->postJson(route('system.update.start'), ['version' => '0.2.0-beta.1'])->assertAccepted();

        Process::assertRan(fn (PendingProcess $process): bool => $process->command === [
            'sudo', '-n', $this->helper, 'update', '0.2.0-beta.1', 'beta',
        ]);
        Http::assertSentCount(1);
    }

    public function test_update_routes_require_authentication(): void
    {
        auth()->logout();

        $this->getJson(route('system.update.show'))->assertUnauthorized();
        $this->postJson(route('system.update.start'), ['version' => '0.2.0'])->assertUnauthorized();
        $this->postJson(route('system.update.rollback'))->assertUnauthorized();

        Http::assertNothingSent();
        Process::assertNothingRan();
    }

    /** @param list<mixed> $releases */
    private function fakeManifest(array $releases, string $channel = 'stable'): void
    {
        Http::fake(['https://updates.example.test/'.$channel.'/releases.json' => Http::response([
            'channel' => $channel, 'latest' => '0.2.0', 'releases' => $releases,
        ])]);
    }

    private function printerState(string $state): void
    {
        $this->mock(PrinterBridge::class, function (MockInterface $mock) use ($state): void {
            $mock->shouldReceive('hasActiveJob')->andReturn(in_array($state, ['printing', 'paused', 'cancelling'], true));
        });
    }

    private function previousRelease(): void
    {
        mkdir($this->home.'/release-before');
        file_put_contents($this->home.'/release-before/VERSION', "0.0.9\n");
        symlink($this->home.'/release-before', $this->home.'/previous');
    }
}
