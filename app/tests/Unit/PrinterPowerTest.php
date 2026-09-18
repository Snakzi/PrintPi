<?php

namespace Tests\Unit;

use App\Services\PrinterBridge;
use PHPUnit\Framework\TestCase;

class PrinterPowerTest extends TestCase
{
    public function test_the_first_running_plugin_with_printer_power_becomes_the_switch(): void
    {
        $statuses = [
            'led-strip' => ['state' => 'running', 'error' => null, 'version' => '1.0.0', 'status' => ['power' => true]],
            'tapo-plug' => [
                'state' => 'running',
                'error' => null,
                'version' => '1.2.0',
                'status' => ['printer_power' => ['id' => 'p1', 'name' => 'MK4S', 'on' => true, 'online' => true], 'plugs' => []],
            ],
        ];

        $this->assertSame(
            ['plugin' => 'tapo-plug', 'id' => 'p1', 'name' => 'MK4S', 'on' => true, 'online' => true],
            PrinterBridge::printerPowerFrom($statuses),
        );
    }

    public function test_stopped_plugins_and_plugins_without_a_printer_plug_offer_no_switch(): void
    {
        $this->assertNull(PrinterBridge::printerPowerFrom([]));
        $this->assertNull(PrinterBridge::printerPowerFrom([
            'tapo-plug' => ['state' => 'running', 'error' => null, 'version' => '1.2.0', 'status' => ['printer_power' => null]],
        ]));
        $this->assertNull(PrinterBridge::printerPowerFrom([
            'tapo-plug' => [
                'state' => 'error',
                'error' => 'boom',
                'version' => '1.2.0',
                'status' => ['printer_power' => ['id' => 'p1', 'name' => 'MK4S', 'on' => false, 'online' => null]],
            ],
        ]));
    }

    public function test_a_running_plugin_with_printer_light_becomes_the_light(): void
    {
        $statuses = [
            'led-strip' => [
                'state' => 'running',
                'error' => null,
                'version' => '1.1.0',
                'status' => ['power' => true, 'printer_light' => ['name' => 'LED strip', 'on' => true, 'color' => '#FF8000']],
            ],
        ];

        $this->assertSame(
            ['plugin' => 'led-strip', 'name' => 'LED strip', 'on' => true, 'color' => '#ff8000'],
            PrinterBridge::printerLightFrom($statuses),
        );
        $this->assertNull(PrinterBridge::printerPowerFrom($statuses));
        $this->assertNull(PrinterBridge::printerLightFrom([
            'led-strip' => ['state' => 'error', 'error' => 'no /dev/mem', 'version' => '1.1.0', 'status' => []],
        ]));
    }

    public function test_a_light_without_a_colour_or_with_a_malformed_one_gets_no_picker(): void
    {
        $light = fn (array $status): ?array => PrinterBridge::printerLightFrom([
            'relay' => ['state' => 'running', 'error' => null, 'version' => '0.1.0', 'status' => ['printer_light' => $status]],
        ]);

        $this->assertSame(['plugin' => 'relay', 'name' => 'Lamp', 'on' => false, 'color' => null], $light(['name' => 'Lamp', 'on' => false]));
        $this->assertNull($light(['name' => 'Lamp', 'on' => true, 'color' => 'warm'])['color']);
        $this->assertNull($light(['name' => 'Lamp', 'on' => true, 'color' => 255])['color']);
    }

    public function test_an_unknown_online_state_stays_null(): void
    {
        $power = PrinterBridge::printerPowerFrom([
            'tapo-plug' => ['state' => 'running', 'error' => null, 'version' => '1.2.0', 'status' => ['printer_power' => ['id' => 'p1', 'on' => false]]],
        ]);

        $this->assertSame(['plugin' => 'tapo-plug', 'id' => 'p1', 'name' => '', 'on' => false, 'online' => null], $power);
    }
}
