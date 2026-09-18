<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\Settings;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class SettingsApiTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->actingAs(User::factory()->create());
    }

    public function test_show_returns_defaults_when_nothing_is_stored(): void
    {
        $this->getJson(route('settings.show'))
            ->assertOk()
            ->assertJson(['serial_port' => null, 'baud_rate' => 115200, 'camera_url' => null, 'camera_device' => null, 'hostname' => null, 'timezone' => null, 'printer_profile' => null, 'printer_name' => null]);
    }

    public function test_update_stores_values_and_keeps_the_rest(): void
    {
        $this->putJson(route('settings.update'), ['serial_port' => '/dev/ttyACM0', 'baud_rate' => 250000])
            ->assertOk()
            ->assertJsonPath('serial_port', '/dev/ttyACM0')
            ->assertJsonPath('baud_rate', 250000)
            ->assertJsonPath('camera_url', null);

        $this->putJson(route('settings.update'), ['camera_url' => 'http://printer.local/webcam/?action=stream'])
            ->assertOk()
            ->assertJsonPath('serial_port', '/dev/ttyACM0')
            ->assertJsonPath('camera_url', 'http://printer.local/webcam/?action=stream');
    }

    public function test_update_rejects_unknown_baud_rate(): void
    {
        $this->putJson(route('settings.update'), ['baud_rate' => 123456])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('baud_rate');
    }

    public function test_update_channel_is_unset_by_default_and_takes_a_published_channel(): void
    {
        config(['printpi.update_channels' => ['stable', 'beta']]);
        $this->getJson(route('settings.show'))->assertOk()->assertJsonPath('update_channel', null);

        $this->putJson(route('settings.update'), ['update_channel' => 'beta'])
            ->assertOk()->assertJsonPath('update_channel', 'beta');
        $this->getJson(route('settings.show'))->assertOk()->assertJsonPath('update_channel', 'beta');
        $this->assertSame('beta', app(Settings::class)->get('update_channel'));
    }

    public function test_update_channel_rejects_channels_the_host_does_not_publish_with_422(): void
    {
        config(['printpi.update_channels' => ['beta']]);

        foreach (['nightly', 'stable'] as $channel) {
            $this->putJson(route('settings.update'), ['update_channel' => $channel])
                ->assertUnprocessable()->assertJsonValidationErrors('update_channel');
        }
        $this->assertDatabaseMissing('settings', ['key' => 'update_channel']);
    }

    public function test_energy_price_and_currency_are_stored(): void
    {
        $this->getJson(route('settings.show'))
            ->assertOk()
            ->assertJsonPath('energy_price', null)
            ->assertJsonPath('currency', '€');

        $this->putJson(route('settings.update'), ['energy_price' => 0.32, 'currency' => 'CHF'])
            ->assertOk()
            ->assertJsonPath('energy_price', 0.32)
            ->assertJsonPath('currency', 'CHF');

        $this->putJson(route('settings.update'), ['energy_price' => -1])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('energy_price');
    }

    public function test_macros_have_defaults_and_can_be_replaced(): void
    {
        $this->getJson(route('settings.show'))
            ->assertOk()
            ->assertJsonPath('macros.0.label', 'Home all')
            ->assertJsonPath('macros.0.gcode', 'G28');

        $this->putJson(route('settings.update'), ['macros' => [
            ['label' => 'Preheat', 'gcode' => "M104 S200\nM140 S60"],
        ]])
            ->assertOk()
            ->assertJsonCount(1, 'macros')
            ->assertJsonPath('macros.0.gcode', "M104 S200\nM140 S60");

        $this->putJson(route('settings.update'), ['macros' => [['label' => '', 'gcode' => 'G28']]])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('macros.0.label');
    }

    public function test_print_and_notification_settings_have_defaults_and_are_validated(): void
    {
        $this->getJson(route('settings.show'))
            ->assertJsonPath('timelapse', true)
            ->assertJsonPath('timelapse_gif', true)
            ->assertJsonPath('timelapse_mp4', true)
            ->assertJsonPath('postcard', true)
            ->assertJsonPath('cancel_gcode', '')
            ->assertJsonPath('history_keep', 0)
            ->assertJsonPath('notify_print_end', true)
            ->assertJsonPath('notify_plugins', true)
            ->assertJsonPath('tab_progress', true);

        $this->putJson(route('settings.update'), ['timelapse' => false, 'postcard' => false, 'cancel_gcode' => "M104 S0\nM140 S0", 'history_keep' => 50, 'tab_progress' => false])
            ->assertOk()
            ->assertJsonPath('timelapse', false)
            ->assertJsonPath('postcard', false)
            ->assertJsonPath('cancel_gcode', "M104 S0\nM140 S0")
            ->assertJsonPath('history_keep', 50)
            ->assertJsonPath('tab_progress', false)
            ->assertJsonPath('notify_plugins', true);

        $this->putJson(route('settings.update'), ['history_keep' => -1])->assertUnprocessable();
        $this->putJson(route('settings.update'), ['timelapse' => 'maybe'])->assertUnprocessable();
    }
}
