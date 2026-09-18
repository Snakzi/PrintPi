<?php

namespace Tests\Feature;

use App\Exceptions\PluginException;
use App\Models\Plugin;
use App\Models\User;
use App\Services\GitCloner;
use App\Services\PrinterBridge;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\File;
use Mockery\MockInterface;
use Tests\TestCase;

class PluginApiTest extends TestCase
{
    use RefreshDatabase;

    private const array LED_DEFAULTS = ['strip_type' => 'ws2812b', 'led_count' => 30, 'gpio_pin' => 18];

    private const array BED_LEVEL_DEFAULTS = [
        'gcode' => "M140 S60\nM104 S170\nM190 S60\nM109 R170\nG28\nG29\nM420 V\nM104 S0\nM140 S0",
        'tolerance' => 0.1,
        'x_min' => 0,
        'x_max' => 0,
        'y_min' => 0,
        'y_max' => 0,
    ];

    private string $installed;

    protected function setUp(): void
    {
        parent::setUp();
        $this->actingAs(User::factory()->create());
        $this->installed = sys_get_temp_dir().'/printpi-plugins-'.uniqid();
        File::ensureDirectoryExists($this->installed);
        config(['printpi.plugins.installed' => $this->installed]);
    }

    protected function tearDown(): void
    {
        File::deleteDirectory($this->installed);
        parent::tearDown();
    }

    public function test_index_lists_the_builtin_plugins_as_available(): void
    {
        $this->mockBridge();

        $this->getJson(route('plugins.index'))
            ->assertOk()
            ->assertJsonCount(4, 'data')
            ->assertJsonPath('data.0.id', 'bed-level-visualizer')
            ->assertJsonPath('data.0.settings', self::BED_LEVEL_DEFAULTS)
            ->assertJsonPath('data.0.controls.0.type', 'mesh')
            ->assertJsonPath('data.1.id', 'led-strip')
            ->assertJsonPath('data.1.source', 'builtin')
            ->assertJsonPath('data.1.installed', false)
            ->assertJsonPath('data.1.enabled', false)
            ->assertJsonPath('data.1.daemon', null)
            ->assertJsonPath('data.1.settings', self::LED_DEFAULTS)
            ->assertJsonPath('data.1.schema.1.key', 'led_count')
            ->assertJsonPath('data.1.controls.0.action', 'set_power')
            ->assertJsonPath('data.2.id', 'tapo-plug')
            ->assertJsonPath('data.2.controls.0.type', 'devices')
            ->assertJsonPath('data.3.id', 'webhook')
            ->assertJsonPath('data.3.settings', ['url' => '', 'secret' => '', 'in_app' => false])
            ->assertJsonPath('data.3.controls.0.type', 'button');
    }

    public function test_sync_command_hands_the_enabled_plugins_to_the_daemon(): void
    {
        $this->mockBridge([], function (MockInterface $mock): void {
            $mock->shouldReceive('syncPlugins')->once()->withArgs(fn (array $plugins): bool => count($plugins) === 1
                && $plugins[0]['id'] === 'bed-level-visualizer'
                && $plugins[0]['settings'] === self::BED_LEVEL_DEFAULTS);
        });
        Plugin::factory()->create(['id' => 'bed-level-visualizer', 'settings' => ['home_first' => true]]);
        Plugin::factory()->create(['id' => 'led-strip', 'enabled' => false]);

        $this->artisan('printpi:sync-plugins')->assertSuccessful();
    }

    public function test_the_bed_level_visualizer_probes_through_its_mesh_control(): void
    {
        $bridge = $this->mockBridge();
        $bridge->shouldReceive('syncPlugins')->once()->withArgs(fn (array $plugins): bool => count($plugins) === 1
            && $plugins[0]['id'] === 'bed-level-visualizer'
            && $plugins[0]['settings'] === self::BED_LEVEL_DEFAULTS);

        $this->postJson(route('plugins.store'), ['id' => 'bed-level-visualizer'])->assertCreated();

        $bridge->shouldReceive('pluginAction')->once()->with('bed-level-visualizer', 'probe', null);
        $this->postJson(route('plugins.action', 'bed-level-visualizer'), ['action' => 'probe'])->assertStatus(202);

        $this->putJson(route('plugins.settings', 'bed-level-visualizer'), ['tolerance' => 0])
            ->assertUnprocessable()->assertJsonValidationErrors('tolerance');
        $this->putJson(route('plugins.settings', 'bed-level-visualizer'), ['gcode' => str_repeat("G4 P1\n", 1000)])
            ->assertUnprocessable()->assertJsonValidationErrors('gcode');
        $bridge->shouldReceive('syncPlugins')->once();
        $this->putJson(route('plugins.settings', 'bed-level-visualizer'), ['gcode' => "G28\nG80\nG81"])
            ->assertOk()
            ->assertJsonPath('settings.gcode', "G28\nG80\nG81")
            ->assertJsonPath('settings.tolerance', 0.1);
    }

    public function test_installing_a_builtin_plugin_enables_it_with_default_settings(): void
    {
        $this->mockBridge([], function (MockInterface $mock): void {
            $mock->shouldReceive('syncPlugins')->once()->withArgs(fn (array $plugins): bool => count($plugins) === 1
                && $plugins[0]['id'] === 'led-strip'
                && str_ends_with($plugins[0]['path'], '/plugins/led-strip')
                && $plugins[0]['version'] === '1.2.0'
                && $plugins[0]['settings'] === self::LED_DEFAULTS);
        });

        $this->postJson(route('plugins.store'), ['id' => 'led-strip'])
            ->assertCreated()
            ->assertJsonPath('installed', true)
            ->assertJsonPath('enabled', true)
            ->assertJsonPath('daemon.state', 'pending');
        $this->assertDatabaseHas('plugins', ['id' => 'led-strip', 'source' => 'builtin', 'enabled' => true]);

        $this->postJson(route('plugins.store'), ['id' => 'led-strip'])->assertUnprocessable();
        $this->postJson(route('plugins.store'), ['id' => 'nope'])->assertNotFound();
        $this->postJson(route('plugins.store'), [])->assertUnprocessable()->assertJsonValidationErrors(['id', 'url']);
    }

    public function test_settings_are_validated_against_the_manifest(): void
    {
        $bridge = $this->mockBridge();
        Plugin::factory()->create(['id' => 'led-strip', 'settings' => self::LED_DEFAULTS]);

        $this->putJson(route('plugins.settings', 'led-strip'), ['led_count' => 0])
            ->assertUnprocessable()->assertJsonValidationErrors('led_count');
        $this->putJson(route('plugins.settings', 'led-strip'), ['gpio_pin' => 7])
            ->assertUnprocessable()->assertJsonValidationErrors('gpio_pin');
        $this->putJson(route('plugins.settings', 'led-strip'), ['strip_type' => 'apa102'])
            ->assertUnprocessable()->assertJsonValidationErrors('strip_type');

        $expected = ['strip_type' => 'ws2812b', 'led_count' => 60, 'gpio_pin' => 10];
        $bridge->shouldReceive('syncPlugins')->once()->withArgs(fn (array $plugins): bool => $plugins[0]['settings'] === $expected);
        $this->putJson(route('plugins.settings', 'led-strip'), ['led_count' => '60', 'gpio_pin' => '10', 'bogus' => 1])
            ->assertOk()
            ->assertJsonPath('settings', $expected);
        $this->assertSame($expected, Plugin::query()->findOrFail('led-strip')->settings);

        $this->putJson(route('plugins.settings', 'other'), ['led_count' => 1])->assertNotFound();
    }

    public function test_disabling_and_uninstalling_take_the_plugin_from_the_daemon(): void
    {
        $bridge = $this->mockBridge([
            'led-strip' => ['state' => 'running', 'error' => null, 'version' => '1.0.0', 'status' => ['backend' => 'spi']],
        ]);
        Plugin::factory()->create(['id' => 'led-strip']);

        $this->getJson(route('plugins.index'))->assertJsonPath('data.1.daemon.status.backend', 'spi');

        $bridge->shouldReceive('syncPlugins')->twice()->with([]);
        $this->putJson(route('plugins.update', 'led-strip'), ['enabled' => false])
            ->assertOk()
            ->assertJsonPath('enabled', false)
            ->assertJsonPath('daemon', null);
        $this->putJson(route('plugins.update', 'led-strip'), ['enabled' => 'maybe'])->assertUnprocessable();

        $bridge->shouldReceive('forgetPlugin')->once()->with('led-strip');
        $this->deleteJson(route('plugins.destroy', 'led-strip'))->assertNoContent();
        $this->assertDatabaseMissing('plugins', ['id' => 'led-strip']);
        $this->assertDirectoryExists(base_path('../plugins/led-strip'));
        $this->deleteJson(route('plugins.destroy', 'led-strip'))->assertNotFound();
    }

    public function test_install_from_git_clones_validates_and_records_the_plugin(): void
    {
        $this->mockBridge([], function (MockInterface $mock): void {
            $mock->shouldReceive('syncPlugins')->once()->withArgs(fn (array $plugins): bool => count($plugins) === 1
                && $plugins[0]['id'] === 'fancy-lights'
                && $plugins[0]['path'] === realpath($this->installed).'/fancy-lights'
                && $plugins[0]['version'] === '2.0.0'
                && $plugins[0]['settings'] === ['level' => 3]);
        });
        $this->mock(GitCloner::class, function (MockInterface $mock): void {
            $mock->shouldReceive('clone')->once()
                ->withArgs(fn (string $url, string $target): bool => $url === 'https://github.com/example/fancy-lights'
                    && str_starts_with($target, $this->installed.'/.clone-'))
                ->andReturnUsing(fn (string $url, string $target) => $this->writePlugin($target, $this->manifest()));
        });

        $this->postJson(route('plugins.store'), ['url' => 'https://github.com/example/fancy-lights'])
            ->assertCreated()
            ->assertJsonPath('id', 'fancy-lights')
            ->assertJsonPath('source', 'git')
            ->assertJsonPath('url', 'https://github.com/example/fancy-lights')
            ->assertJsonPath('version', '2.0.0')
            ->assertJsonPath('settings.level', 3);
        $this->assertFileExists($this->installed.'/fancy-lights/plugin.json');
        $this->assertDatabaseHas('plugins', ['id' => 'fancy-lights', 'source' => 'git']);
        $this->assertCount(1, File::directories($this->installed));

        $this->deleteJson(route('plugins.destroy', 'fancy-lights'))->assertNoContent();
        $this->assertDirectoryDoesNotExist($this->installed.'/fancy-lights');
    }

    public function test_install_from_git_rejects_bad_clones(): void
    {
        $this->mockBridge([], fn (MockInterface $mock) => $mock->shouldNotReceive('syncPlugins'));
        $this->mock(GitCloner::class, function (MockInterface $mock): void {
            $mock->shouldReceive('clone')->once()->andReturnUsing(function (string $url, string $target): void {
                File::ensureDirectoryExists($target);
                File::put($target.'/plugin.json', '{not json');
            });
            $mock->shouldReceive('clone')->once()
                ->andReturnUsing(fn (string $url, string $target) => $this->writePlugin($target, $this->manifest('led-strip')));
            $mock->shouldReceive('clone')->once()->andThrow(new PluginException('git failed: repository not found'));
        });

        $this->postJson(route('plugins.store'), ['url' => 'https://github.com/example/broken'])
            ->assertUnprocessable()
            ->assertJsonPath('message', fn (string $message): bool => str_contains($message, 'valid JSON'));
        $this->postJson(route('plugins.store'), ['url' => 'https://github.com/example/clash'])
            ->assertUnprocessable()
            ->assertJsonPath('message', fn (string $message): bool => str_contains($message, 'led-strip'));
        $this->postJson(route('plugins.store'), ['url' => 'https://github.com/example/missing'])
            ->assertUnprocessable()
            ->assertJsonPath('message', 'git failed: repository not found');
        $this->postJson(route('plugins.store'), ['url' => 'http://github.com/example/plain'])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('url');

        $this->assertCount(0, File::directories($this->installed));
        $this->assertDatabaseCount('plugins', 0);
    }

    public function test_actions_are_forwarded_to_the_daemon(): void
    {
        $bridge = $this->mockBridge();
        Plugin::factory()->create(['id' => 'led-strip']);

        $bridge->shouldReceive('pluginAction')->once()->with('led-strip', 'set_color', '#ff0000');
        $this->postJson(route('plugins.action', 'led-strip'), ['action' => 'set_color', 'value' => '#ff0000'])
            ->assertStatus(202);

        $bridge->shouldReceive('pluginAction')->once()->with('led-strip', 'set_color', ['id' => 'p1', 'name' => 'Lamp']);
        $this->postJson(route('plugins.action', 'led-strip'), ['action' => 'set_color', 'value' => ['id' => 'p1', 'name' => 'Lamp']])
            ->assertStatus(202);

        $this->postJson(route('plugins.action', 'led-strip'), ['action' => 'rainbow'])->assertUnprocessable();
        $this->postJson(route('plugins.action', 'led-strip'), ['action' => 'set_color', 'value' => ['a' => ['b' => 1]]])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('value');

        Plugin::query()->whereKey('led-strip')->update(['enabled' => false]);
        $this->postJson(route('plugins.action', 'led-strip'), ['action' => 'set_power', 'value' => true])
            ->assertUnprocessable();
    }

    public function test_upgrade_pulls_a_git_plugin_and_rereads_its_manifest(): void
    {
        $this->mockBridge([], function (MockInterface $mock): void {
            $mock->shouldReceive('syncPlugins')->once()->withArgs(fn (array $plugins): bool => $plugins[0]['version'] === '2.1.0'
                && $plugins[0]['settings'] === ['level' => 5, 'name' => 'Lights']);
        });
        $directory = $this->installed.'/fancy-lights';
        $this->writePlugin($directory, $this->manifest());
        Plugin::factory()->fromGit()->create(['id' => 'fancy-lights', 'version' => '2.0.0', 'settings' => ['level' => 5]]);
        $this->mock(GitCloner::class, function (MockInterface $mock) use ($directory): void {
            $mock->shouldReceive('pull')->once()->with(realpath($directory))->andReturnUsing(function () use ($directory): void {
                $this->writePlugin($directory, $this->manifest('fancy-lights', [
                    'version' => '2.1.0',
                    'settings' => [
                        ['key' => 'level', 'label' => 'Level', 'type' => 'integer', 'default' => 3, 'min' => 0, 'max' => 10],
                        ['key' => 'name', 'label' => 'Name', 'type' => 'string', 'default' => 'Lights'],
                    ],
                ]));
            });
        });

        $this->postJson(route('plugins.upgrade', 'fancy-lights'))
            ->assertOk()
            ->assertJsonPath('version', '2.1.0')
            ->assertJsonPath('settings.name', 'Lights');
        $this->assertDatabaseHas('plugins', ['id' => 'fancy-lights', 'version' => '2.1.0']);

        Plugin::factory()->create(['id' => 'led-strip']);
        $this->postJson(route('plugins.upgrade', 'led-strip'))->assertUnprocessable();
    }

    /**
     * @param  array<string, array<string, mixed>>  $statuses
     */
    private function mockBridge(array $statuses = [], ?callable $expectations = null): MockInterface
    {
        return $this->mock(PrinterBridge::class, function (MockInterface $mock) use ($statuses, $expectations): void {
            $mock->shouldReceive('pluginStatuses')->andReturn($statuses)->byDefault();
            $mock->shouldReceive('syncPlugins')->byDefault();
            $mock->shouldReceive('forgetPlugin')->byDefault();
            if ($expectations !== null) {
                $expectations($mock);
            }
        });
    }

    /**
     * @param  array<string, mixed>  $manifest
     */
    private function writePlugin(string $directory, array $manifest): void
    {
        File::ensureDirectoryExists($directory.'/daemon');
        File::put($directory.'/plugin.json', json_encode($manifest, JSON_THROW_ON_ERROR));
        File::put($directory.'/daemon/plugin.py', "from printpi_daemon.plugins import PluginBase\n\nclass Plugin(PluginBase):\n    pass\n");
    }

    /**
     * @param  array<string, mixed>  $overrides
     * @return array<string, mixed>
     */
    private function manifest(string $id = 'fancy-lights', array $overrides = []): array
    {
        return array_merge([
            'id' => $id,
            'name' => 'Fancy Lights',
            'version' => '2.0.0',
            'description' => 'Test plugin',
            'settings' => [['key' => 'level', 'label' => 'Level', 'type' => 'integer', 'default' => 3, 'min' => 0, 'max' => 10]],
            'controls' => [['key' => 'level', 'label' => 'Level', 'type' => 'range', 'action' => 'set_level', 'min' => 0, 'max' => 10]],
        ], $overrides);
    }
}
