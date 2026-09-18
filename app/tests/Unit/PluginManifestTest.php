<?php

namespace Tests\Unit;

use App\Exceptions\PluginException;
use App\Services\PluginManifest;
use Illuminate\Support\Facades\Validator;
use Tests\TestCase;

class PluginManifestTest extends TestCase
{
    public function test_it_rejects_manifests_that_break_the_contract(): void
    {
        $broken = [
            [],
            ['id' => 'Bad Id', 'name' => 'x', 'version' => '1'],
            ['id' => 'ok', 'name' => 'x', 'version' => 1],
            ['id' => 'ok', 'name' => 'x', 'version' => '1', 'settings' => [['key' => 'a', 'label' => 'A', 'type' => 'select']]],
            ['id' => 'ok', 'name' => 'x', 'version' => '1', 'settings' => [['key' => 'a', 'label' => 'A', 'type' => 'wat']]],
            ['id' => 'ok', 'name' => 'x', 'version' => '1', 'controls' => [['key' => 'a', 'label' => 'A', 'type' => 'toggle']]],
            ['id' => 'ok', 'name' => 'x', 'version' => '1', 'controls' => [['key' => 'a', 'label' => 'A', 'type' => 'devices', 'action' => 'scan', 'actions' => ['Add Me']]]],
        ];
        foreach ($broken as $data) {
            try {
                PluginManifest::fromArray($data);
                $this->fail('Accepted '.json_encode($data));
            } catch (PluginException $exception) {
                $this->assertStringStartsWith('Invalid plugin.json', $exception->getMessage());
            }
        }
    }

    public function test_defaults_rules_and_normalization_follow_the_schema(): void
    {
        $manifest = PluginManifest::fromArray([
            'id' => 'demo',
            'name' => 'Demo',
            'version' => '0.1',
            'settings' => [
                ['key' => 'count', 'label' => 'Count', 'type' => 'integer', 'min' => 1, 'max' => 10],
                ['key' => 'mode', 'label' => 'Mode', 'type' => 'select', 'options' => [['value' => 1, 'label' => 'One'], ['value' => 2, 'label' => 'Two']]],
                ['key' => 'on', 'label' => 'On', 'type' => 'boolean', 'default' => true],
                ['key' => 'tint', 'label' => 'Tint', 'type' => 'color'],
                ['key' => 'ratio', 'label' => 'Ratio', 'type' => 'number', 'default' => '0.5'],
                ['key' => 'note', 'label' => 'Note', 'type' => 'string'],
            ],
        ]);

        $this->assertSame(['count' => 1, 'mode' => 1, 'on' => true, 'tint' => '#ffffff', 'ratio' => 0.5, 'note' => ''], $manifest->defaults());
        $this->assertTrue(Validator::make(['count' => 5, 'mode' => '2', 'on' => true, 'tint' => '#ABCDEF'], $manifest->rules())->passes());
        $this->assertFalse(Validator::make(['on' => 'yes'], $manifest->rules())->passes());
        $this->assertTrue(Validator::make([], $manifest->rules())->passes());
        $this->assertFalse(Validator::make(['count' => 11], $manifest->rules())->passes());
        $this->assertFalse(Validator::make(['mode' => 3], $manifest->rules())->passes());
        $this->assertFalse(Validator::make(['tint' => 'red'], $manifest->rules())->passes());
        $this->assertSame(
            ['count' => 5, 'mode' => 2, 'on' => true, 'tint' => '#ABCDEF'],
            $manifest->normalize(['count' => '5', 'mode' => '2', 'on' => 'true', 'tint' => '#ABCDEF', 'extra' => 1]),
        );
        $this->assertFalse($manifest->hasAction('anything'));
        $this->assertSame([], $manifest->toArray()['controls']);
    }

    public function test_the_builtin_led_strip_manifest_is_valid(): void
    {
        $manifest = PluginManifest::fromDirectory(base_path('../plugins/led-strip'));

        $this->assertSame('led-strip', $manifest->id);
        $this->assertTrue($manifest->daemon);
        $this->assertSame(['strip_type' => 'ws2812b', 'led_count' => 30, 'gpio_pin' => 18], $manifest->defaults());
        $this->assertTrue($manifest->hasAction('set_color'));
        $this->assertTrue($manifest->hasAction('printer_light_on'));
        $this->assertTrue($manifest->hasAction('printer_light_color'));
        $this->assertFalse($manifest->hasAction('rainbow'));
    }

    public function test_the_builtin_tapo_plug_manifest_declares_the_device_actions(): void
    {
        $manifest = PluginManifest::fromDirectory(base_path('../plugins/tapo-plug'));

        $this->assertSame('tapo-plug', $manifest->id);
        $this->assertSame(['username' => '', 'password' => '', 'auto_connect' => true, 'auto_off' => false, 'auto_off_minutes' => 5], $manifest->defaults());
        $this->assertSame('password', $manifest->toArray()['schema'][1]['type']);
        $this->assertSame('devices', $manifest->controls[0]['type']);
        foreach (['scan', 'add', 'rename', 'remove', 'turn_on', 'turn_off', 'set_printer', 'printer_power_on', 'printer_power_off'] as $action) {
            $this->assertTrue($manifest->hasAction($action), $action);
        }
        $this->assertFalse($manifest->hasAction('plugs'));
        $this->assertTrue(Validator::make(['username' => 'me@example.com', 'password' => 'secret'], $manifest->rules())->passes());
    }
}
