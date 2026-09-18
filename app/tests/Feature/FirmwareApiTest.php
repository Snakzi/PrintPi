<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\Firmware;
use App\Services\PrinterBridge;
use App\Services\Settings;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Request;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Mockery\MockInterface;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

class FirmwareApiTest extends TestCase
{
    use RefreshDatabase;

    private const string BUDDY_RELEASES = 'https://api.github.com/repos/prusa3d/Prusa-Firmware-Buddy/releases*';

    private const string PRUSA_RELEASES = 'https://api.github.com/repos/prusa3d/Prusa-Firmware/releases*';

    private const string MK4S_ASSET = 'https://github.com/prusa3d/Prusa-Firmware-Buddy/releases/download/v6.5.7/MK4_MK4S_MK3.9_MK3.9S_firmware_6.5.7.bbf';

    private const string MK3S_ASSET = 'https://github.com/prusa3d/Prusa-Firmware/releases/download/v3.14.1/MK3S_MK3S%2B_FW_3.14.1_MULTILANG.hex';

    private MockInterface $bridge;

    /**
     * What the mocked bridge answers; a test changes it between requests, since the
     * route keeps its controller and with it the first bridge it was given.
     *
     * @var array{printer: array<string, mixed>, status: array<string, mixed>, files: list<array{name: string, size: ?int, long_name: ?string}>, connected: bool, job: bool, alive: bool}
     */
    private array $daemon = ['printer' => [], 'status' => [], 'files' => [], 'connected' => true, 'job' => false, 'alive' => true];

    protected function setUp(): void
    {
        parent::setUp();
        $this->actingAs(User::factory()->create());
        Http::preventStrayRequests();
        Storage::fake('gcode');
        config(['app.timezone' => 'Europe/Berlin']);
        $this->bridge = $this->mock(PrinterBridge::class, function (MockInterface $mock): void {
            $mock->shouldReceive('printer')->andReturnUsing(fn (): array => $this->daemon['printer']
                + ['connection' => $this->daemon['connected'] ? 'connected' : 'offline', 'firmware' => []]);
            $mock->shouldReceive('isConnected')->andReturnUsing(fn (): bool => $this->daemon['connected']);
            $mock->shouldReceive('hasActiveJob')->andReturnUsing(fn (): bool => $this->daemon['job']);
            $mock->shouldReceive('isDaemonAlive')->andReturnUsing(fn (): bool => $this->daemon['alive']);
            $mock->shouldReceive('firmwareStatus')->andReturnUsing(fn (): array => $this->daemon['status'] + ['phase' => 'idle', 'avrdude_available' => true]);
            $mock->shouldReceive('isFlashingFirmware')->andReturnUsing(fn (): bool => in_array($this->daemon['status']['phase'] ?? 'idle', PrinterBridge::ACTIVE_FIRMWARE_PHASES, true));
            $mock->shouldReceive('firmwareFiles')->andReturnUsing(fn (): array => [
                'files' => $this->daemon['files'], 'listed_at' => $this->daemon['files'] === [] ? null : 1758000000.0, 'error' => null,
            ]);
        });
    }

    /**
     * Releases the way GitHub lists them: several trains in one repository, newest first,
     * with a prerelease and a draft that must not count.
     *
     * @return list<array<string, mixed>>
     */
    private static function buddyReleases(): array
    {
        $release = static fn (string $tag, array $assets, bool $prerelease = false, bool $draft = false): array => [
            'tag_name' => $tag,
            'prerelease' => $prerelease,
            'draft' => $draft,
            'published_at' => '2026-06-18T10:00:00Z',
            'html_url' => "https://github.com/prusa3d/Prusa-Firmware-Buddy/releases/tag/{$tag}",
            'body' => "Notes for {$tag}",
            'assets' => array_map(static fn (string $name): array => [
                'name' => $name,
                'size' => 4100840,
                'browser_download_url' => "https://github.com/prusa3d/Prusa-Firmware-Buddy/releases/download/{$tag}/{$name}",
            ], $assets),
        ];

        return [
            $release('v6.9.1-beta', ['COREONE_COREONE+GEN2_INDX_firmware_6.9.1-beta.bbf', 'MK4_MK4S_MK3.9_MK3.9S_firmware_6.9.1-beta.bbf'], prerelease: true),
            $release('v7.0.0', ['MK4_MK4S_MK3.9_MK3.9S_firmware_7.0.0.bbf'], draft: true),
            $release('v6.10.1', ['XL_XL+_firmware_6.10.1.bbf']),
            $release('v6.9.0', ['COREONE_COREONE+GEN2_INDX_firmware_6.9.0.bbf']),
            $release('v6.5.7', ['COREONE_COREONE+_6.5.7.bbf', 'MK3.5_MK3.5S_firmware_6.5.7.bbf', 'MK4_MK4S_MK3.9_MK3.9S_firmware_6.5.7.bbf']),
            $release('v6.4.2', ['MINI_english-german_firmware_6.4.2.bbf', 'XL_firmware_6.4.2.bbf']),
            $release('v6.5.3', ['MK4_MK4S_MK3.9_MK3.9S_firmware_6.5.3.bbf']),
            ['tag_name' => 'not-a-version', 'assets' => [['name' => 'MK4S_firmware.bbf', 'browser_download_url' => 'https://example.test/x.bbf']]],
            'garbage',
        ];
    }

    /**
     * @param  array<string, mixed>  $printer
     * @param  array<string, mixed>  $status
     * @param  list<array{name: string, size: ?int, long_name: ?string}>  $files
     */
    private function mockBridge(array $printer = [], array $status = [], array $files = [], bool $connected = true, bool $job = false, bool $alive = true): MockInterface
    {
        $this->daemon = compact('printer', 'status', 'files', 'connected', 'job', 'alive');

        return $this->bridge;
    }

    private function useProfile(string $id): void
    {
        app(Settings::class)->set(['printer_profile' => $id]);
    }

    public function test_show_reports_the_buddy_method_the_installed_version_and_the_newest_release_for_the_family(): void
    {
        $this->travelTo(CarbonImmutable::parse('2026-09-15T16:00:00Z'));
        $this->useProfile('prusa-mk4s');
        Http::fake([self::BUDDY_RELEASES => Http::response(self::buddyReleases())]);
        $files = [['name' => 'MK4_MK~1.BBF', 'size' => null, 'long_name' => null]];
        $this->mockBridge(['firmware' => ['FIRMWARE_NAME' => 'Prusa-Firmware-Buddy 6.4.0+14924 (Github)', 'MACHINE_TYPE' => 'Prusa-MK4S']], files: $files);

        $this->getJson(route('printer.firmware.show'))->assertOk()->assertExactJson([
            'profile' => ['id' => 'prusa-mk4s', 'model' => 'Original Prusa MK4S', 'firmware' => 'buddy', 'family' => 'MK4S'],
            'method' => 'buddy',
            'methods' => ['buddy', 'avrdude', 'restart'],
            'connected' => true,
            'installed' => ['name' => 'Prusa-Firmware-Buddy 6.4.0+14924 (Github)', 'version' => '6.4.0'],
            'latest' => [
                'version' => '6.5.7',
                'date' => '2026-06-18T10:00:00Z',
                'notes' => 'Notes for v6.5.7',
                'name' => 'MK4_MK4S_MK3.9_MK3.9S_firmware_6.5.7.bbf',
                'size' => 4100840,
                'url' => self::MK4S_ASSET,
                'page' => 'https://github.com/prusa3d/Prusa-Firmware-Buddy/releases/tag/v6.5.7',
            ],
            'up_to_date' => false,
            'checked_at' => '2026-09-15T18:00:00+02:00',
            'error' => null,
            'avrdude' => ['mcu' => 'atmega1284p', 'programmer' => 'arduino', 'baud' => 115200],
            'status' => ['phase' => 'idle', 'avrdude_available' => true],
            'files' => ['files' => $files, 'listed_at' => 1758000000.0, 'error' => null],
        ]);

        Http::assertSent(fn (Request $request): bool => $request->method() === 'GET'
            && str_starts_with($request->url(), 'https://api.github.com/repos/prusa3d/Prusa-Firmware-Buddy/releases?')
            && $request->hasHeader('Accept', 'application/vnd.github+json'));
        Http::assertSentCount(1);
    }

    public function test_show_finds_the_xl_train_and_the_mk3s_hex(): void
    {
        $this->useProfile('prusa-xl');
        Http::fake([self::BUDDY_RELEASES => Http::response(self::buddyReleases())]);
        $this->mockBridge(['firmware' => ['FIRMWARE_NAME' => 'Prusa-Firmware-Buddy 6.10.1+13579 (Github)']]);

        $this->getJson(route('printer.firmware.show'))->assertOk()
            ->assertJsonPath('latest.version', '6.10.1')
            ->assertJsonPath('latest.name', 'XL_XL+_firmware_6.10.1.bbf')
            ->assertJsonPath('up_to_date', true);

        $this->useProfile('prusa-mk3s');
        Http::fake([self::PRUSA_RELEASES => Http::response([[
            'tag_name' => 'v3.14.1', 'prerelease' => false, 'draft' => false, 'published_at' => '2024-11-28T12:42:21Z', 'body' => null,
            'assets' => [
                ['name' => 'E3D_REVO_FW_MK3_MK3S_MK3S+_FW_3.14.1.zip', 'size' => 1, 'browser_download_url' => 'https://example.test/revo.zip'],
                ['name' => 'MK3_FW_3.14.1_MULTILANG.hex', 'size' => 2, 'browser_download_url' => 'https://example.test/mk3.hex'],
                ['name' => 'MK3S_MK3S+_FW_3.14.1_MULTILANG.hex', 'size' => 3, 'browser_download_url' => self::MK3S_ASSET],
                ['name' => 'MMU2S_MMU3_FW3.0.3+896.hex', 'size' => 4, 'browser_download_url' => 'https://example.test/mmu.hex'],
            ],
        ]])]);
        $this->mockBridge(['firmware' => ['FIRMWARE_NAME' => 'Prusa-Firmware 3.13.3 based on Marlin']]);

        $this->getJson(route('printer.firmware.show'))->assertOk()
            ->assertJsonPath('method', 'avrdude')
            ->assertJsonPath('installed.version', '3.13.3')
            ->assertJsonPath('latest.version', '3.14.1')
            ->assertJsonPath('latest.name', 'MK3S_MK3S+_FW_3.14.1_MULTILANG.hex')
            ->assertJsonPath('latest.url', self::MK3S_ASSET)
            ->assertJsonPath('up_to_date', false)
            ->assertJsonPath('avrdude', ['mcu' => 'atmega2560', 'programmer' => 'wiring', 'baud' => 115200]);
    }

    public function test_show_without_a_connection_knows_no_installed_version(): void
    {
        $this->useProfile('prusa-mk4s');
        Http::fake([self::BUDDY_RELEASES => Http::response(self::buddyReleases())]);
        $this->mockBridge(connected: false);

        $this->getJson(route('printer.firmware.show'))->assertOk()
            ->assertJsonPath('connected', false)
            ->assertJsonPath('installed', ['name' => null, 'version' => null])
            ->assertJsonPath('latest.version', '6.5.7')
            ->assertJsonPath('up_to_date', null);
    }

    public function test_show_for_a_generic_marlin_printer_restarts_and_looks_nothing_up(): void
    {
        $this->useProfile('creality-ender-3');
        Http::fake();
        $this->mockBridge(['firmware' => ['FIRMWARE_NAME' => 'Marlin 2.1.2.4 (Sep 15 2026)']]);

        $this->getJson(route('printer.firmware.show'))->assertOk()
            ->assertJsonPath('method', 'restart')
            ->assertJsonPath('installed.version', '2.1.2.4')
            ->assertJsonPath('latest', null)
            ->assertJsonPath('up_to_date', null)
            ->assertJsonPath('checked_at', null);
        Http::assertNothingSent();
    }

    public function test_show_for_an_unflashable_printer_or_no_profile_offers_no_method(): void
    {
        $this->useProfile('klipper');
        Http::fake();
        $this->mockBridge();

        $this->getJson(route('printer.firmware.show'))->assertOk()
            ->assertJsonPath('method', null)->assertJsonPath('methods', []);

        app(Settings::class)->set(['printer_profile' => null]);
        $this->getJson(route('printer.firmware.show'))->assertOk()
            ->assertJsonPath('profile', null)->assertJsonPath('method', null);
        Http::assertNothingSent();
    }

    public function test_releases_are_cached_for_a_day_and_a_failed_check_keeps_the_last_release(): void
    {
        $this->travelTo(CarbonImmutable::parse('2026-09-15T16:00:00Z'));
        $this->useProfile('prusa-mk4s');
        Http::fake([self::BUDDY_RELEASES => Http::sequence()
            ->push(self::buddyReleases())
            ->pushStatus(503)]);
        $this->mockBridge();

        $this->getJson(route('printer.firmware.show'))->assertJsonPath('latest.version', '6.5.7');
        $this->travel(23)->hours();
        $this->getJson(route('printer.firmware.show'))->assertJsonPath('latest.version', '6.5.7');
        Http::assertSentCount(1);

        $this->getJson(route('printer.firmware.show', ['check' => 1]))->assertOk()
            ->assertJsonPath('latest.version', '6.5.7')
            ->assertJsonPath('checked_at', '2026-09-15T18:00:00+02:00')
            ->assertJsonPath('error', 'GitHub could not be reached.');
        Http::assertSentCount(2);
    }

    public function test_files_asks_the_daemon_for_a_listing_when_the_printer_is_free(): void
    {
        $this->mockBridge()->shouldReceive('listFirmwareFiles')->once();

        $this->postJson(route('printer.firmware.files'))->assertStatus(202)->assertJsonPath('queued', true);
    }

    public function test_files_is_refused_without_a_connection_or_during_a_print(): void
    {
        $this->mockBridge(connected: false)->shouldNotReceive('listFirmwareFiles');
        $this->postJson(route('printer.firmware.files'))->assertStatus(409)
            ->assertJsonPath('message', 'The printer is not connected.');

        $this->mockBridge(job: true)->shouldNotReceive('listFirmwareFiles');
        $this->postJson(route('printer.firmware.files'))->assertStatus(409)
            ->assertJsonPath('message', 'A print is running.');
    }

    public function test_flash_buddy_hands_the_daemon_a_file_from_the_drive_listing(): void
    {
        $this->useProfile('prusa-mk4s');
        $files = [['name' => 'MK4_MK~1.BBF', 'size' => null, 'long_name' => null], ['name' => 'CUBE~1.GCO', 'size' => 12, 'long_name' => null]];
        $this->mockBridge(files: $files)->shouldReceive('flashFirmware')->once()
            ->with(['method' => 'buddy', 'file' => 'MK4_MK~1.BBF']);

        $this->postJson(route('printer.firmware.flash'), ['name' => 'MK4_MK~1.BBF'])->assertStatus(202)
            ->assertExactJson(['status' => 'flashing', 'method' => 'buddy', 'file' => 'MK4_MK~1.BBF']);
    }

    #[DataProvider('badDriveFiles')]
    public function test_flash_buddy_rejects_files_that_are_not_bbf_or_not_on_the_drive(array $body, string $message): void
    {
        $this->useProfile('prusa-mk4s');
        $files = [['name' => 'MK4_MK~1.BBF', 'size' => null, 'long_name' => null], ['name' => 'CUBE~1.GCO', 'size' => 12, 'long_name' => null]];
        $this->mockBridge(files: $files)->shouldNotReceive('flashFirmware');

        $this->postJson(route('printer.firmware.flash'), $body)->assertStatus(422)
            ->assertJsonPath('errors.name.0', $message);
    }

    /**
     * @return array<string, array{0: array<string, mixed>, 1: string}>
     */
    public static function badDriveFiles(): array
    {
        return [
            'missing' => [[], 'Choose a firmware file on the printer\'s USB drive.'],
            'gcode' => [['name' => 'CUBE~1.GCO'], 'Buddy firmware files end with .bbf.'],
            'unknown' => [['name' => 'OTHER.BBF'], 'This file is not on the printer\'s USB drive.'],
            'path' => [['name' => '../OTHER.BBF'], 'The name field format is invalid.'],
        ];
    }

    public function test_flash_is_refused_while_the_printer_is_busy(): void
    {
        $this->useProfile('prusa-mk4s');
        $files = [['name' => 'MK4_MK~1.BBF', 'size' => null, 'long_name' => null]];

        $this->mockBridge(files: $files, job: true)->shouldNotReceive('flashFirmware');
        $this->postJson(route('printer.firmware.flash'), ['name' => 'MK4_MK~1.BBF'])->assertStatus(409)
            ->assertJsonPath('message', 'A print is running.');

        $this->mockBridge(['firmware' => []], ['phase' => 'rebooting'], $files)->shouldNotReceive('flashFirmware');
        $this->postJson(route('printer.firmware.flash'), ['name' => 'MK4_MK~1.BBF'])->assertStatus(409)
            ->assertJsonPath('message', 'A firmware update is already running.');

        $this->mockBridge(files: $files, connected: false)->shouldNotReceive('flashFirmware');
        $this->postJson(route('printer.firmware.flash'), ['name' => 'MK4_MK~1.BBF'])->assertStatus(409)
            ->assertJsonPath('message', 'The printer is not connected.');

        $this->mockBridge(files: $files, alive: false)->shouldNotReceive('flashFirmware');
        $this->postJson(route('printer.firmware.flash'), ['name' => 'MK4_MK~1.BBF'])->assertStatus(503);

        $this->useProfile('klipper');
        $this->mockBridge()->shouldNotReceive('flashFirmware');
        $this->postJson(route('printer.firmware.flash'))->assertStatus(409)
            ->assertJsonPath('message', 'This printer cannot be updated from PrintPi.');
    }

    public function test_flash_avrdude_stores_the_upload_and_passes_its_path_with_the_board_parameters(): void
    {
        $this->useProfile('prusa-mk3s');
        app(Settings::class)->set(['firmware_baud' => 57600]);
        $path = Storage::disk('gcode')->path('firmware/MK3S_MK3S+_FW_3.14.1_MULTILANG.hex');
        $this->mockBridge(connected: false)->shouldReceive('flashFirmware')->once()
            ->with(['method' => 'avrdude', 'file' => $path, 'mcu' => 'atmega2560', 'programmer' => 'wiring', 'baud' => 57600]);

        $upload = UploadedFile::fake()->createWithContent('MK3S_MK3S+_FW_3.14.1_MULTILANG.hex', ":00000001FF\n");
        $this->post(route('printer.firmware.flash'), ['file' => $upload], ['Accept' => 'application/json'])
            ->assertStatus(202)
            ->assertJsonPath('file', 'MK3S_MK3S+_FW_3.14.1_MULTILANG.hex');

        Storage::disk('gcode')->assertExists('firmware/MK3S_MK3S+_FW_3.14.1_MULTILANG.hex');
        $this->assertSame(":00000001FF\n", Storage::disk('gcode')->get('firmware/MK3S_MK3S+_FW_3.14.1_MULTILANG.hex'));
    }

    public function test_flash_avrdude_downloads_the_newest_release(): void
    {
        $this->useProfile('prusa-mk3s');
        Http::fake([
            self::PRUSA_RELEASES => Http::response([[
                'tag_name' => 'v3.14.1', 'prerelease' => false, 'draft' => false,
                'assets' => [['name' => 'MK3S_MK3S+_FW_3.14.1_MULTILANG.hex', 'size' => 3, 'browser_download_url' => self::MK3S_ASSET]],
            ]]),
            self::MK3S_ASSET => Http::response(":0100000000FF\n"),
        ]);
        $path = Storage::disk('gcode')->path('firmware/MK3S_MK3S+_FW_3.14.1_MULTILANG.hex');
        $this->mockBridge()->shouldReceive('flashFirmware')->once()
            ->with(['method' => 'avrdude', 'file' => $path, 'mcu' => 'atmega2560', 'programmer' => 'wiring', 'baud' => 115200]);

        $this->postJson(route('printer.firmware.flash'), ['source' => 'release'])->assertStatus(202)
            ->assertJsonPath('file', 'MK3S_MK3S+_FW_3.14.1_MULTILANG.hex');
        $this->assertSame(":0100000000FF\n", Storage::disk('gcode')->get('firmware/MK3S_MK3S+_FW_3.14.1_MULTILANG.hex'));
    }

    public function test_flash_avrdude_reports_a_failed_download_and_needs_a_file_otherwise(): void
    {
        $this->useProfile('prusa-mk3s');
        Http::fake([
            self::PRUSA_RELEASES => Http::response([[
                'tag_name' => 'v3.14.1', 'prerelease' => false, 'draft' => false,
                'assets' => [['name' => 'MK3S_MK3S+_FW_3.14.1_MULTILANG.hex', 'size' => 3, 'browser_download_url' => self::MK3S_ASSET]],
            ]]),
            self::MK3S_ASSET => Http::response('', 500),
        ]);
        $this->mockBridge()->shouldNotReceive('flashFirmware');

        $this->postJson(route('printer.firmware.flash'), ['source' => 'release'])->assertStatus(502)
            ->assertJsonPath('message', 'The firmware could not be downloaded.');
        $this->postJson(route('printer.firmware.flash'))->assertStatus(422)
            ->assertJsonPath('errors.file.0', 'Upload a firmware file.');
        $this->post(route('printer.firmware.flash'), ['file' => UploadedFile::fake()->create('firmware.gcode', 1)], ['Accept' => 'application/json'])
            ->assertStatus(422)->assertJsonValidationErrors('file');
    }

    public function test_flash_restart_needs_only_a_connection(): void
    {
        $this->useProfile('creality-ender-3');
        $this->mockBridge()->shouldReceive('flashFirmware')->once()->with(['method' => 'restart', 'file' => null]);
        $this->postJson(route('printer.firmware.flash'))->assertStatus(202)
            ->assertExactJson(['status' => 'flashing', 'method' => 'restart', 'file' => null]);

        $this->mockBridge(connected: false)->shouldNotReceive('flashFirmware');
        $this->postJson(route('printer.firmware.flash'))->assertStatus(409);
    }

    public function test_firmware_settings_override_the_profile_method_and_board(): void
    {
        $this->useProfile('creality-ender-3');
        $this->mockBridge();
        Http::fake();

        $this->putJson(route('settings.update'), ['firmware_method' => 'avrdude', 'firmware_mcu' => 'atmega1284p', 'firmware_programmer' => 'arduino', 'firmware_baud' => 115200])
            ->assertOk()->assertJsonPath('firmware_method', 'avrdude');
        $this->getJson(route('printer.firmware.show'))->assertOk()
            ->assertJsonPath('method', 'avrdude')
            ->assertJsonPath('avrdude', ['mcu' => 'atmega1284p', 'programmer' => 'arduino', 'baud' => 115200]);

        $this->putJson(route('settings.update'), ['firmware_method' => 'dfu'])->assertStatus(422)->assertJsonValidationErrors('firmware_method');
        $this->putJson(route('settings.update'), ['firmware_mcu' => 'ATmega 2560'])->assertStatus(422)->assertJsonValidationErrors('firmware_mcu');
        $this->putJson(route('settings.update'), ['firmware_baud' => 12345])->assertStatus(422)->assertJsonValidationErrors('firmware_baud');
        $this->putJson(route('settings.update'), ['firmware_method' => null])->assertOk()->assertJsonPath('firmware_method', null);
        $this->getJson(route('printer.firmware.show'))->assertJsonPath('method', 'restart');
    }

    #[DataProvider('firmwareNames')]
    public function test_version_is_read_from_the_firmware_name(?string $name, ?string $version): void
    {
        $this->assertSame($version, Firmware::versionOf($name));
    }

    /**
     * @return array<string, array{0: ?string, 1: ?string}>
     */
    public static function firmwareNames(): array
    {
        return [
            'buddy' => ['Prusa-Firmware-Buddy 6.4.0+14924 (Github)', '6.4.0'],
            'buddy rc' => ['Prusa-Firmware-Buddy 6.5.3-RC+13570 (Github)', '6.5.3'],
            'prusa' => ['Prusa-Firmware 3.14.1 based on Marlin', '3.14.1'],
            'marlin' => ['Marlin 2.1.2.4 (Sep 15 2026)', '2.1.2.4'],
            'marlin bugfix' => ['Marlin bugfix-2.1.x (Sep 15 2026)', null],
            'none' => [null, null],
        ];
    }
}
