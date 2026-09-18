<?php

namespace Tests\Unit;

use App\Models\Spool;
use PHPUnit\Framework\TestCase;

class SpoolTest extends TestCase
{
    public function test_length_and_mass_convert_through_diameter_and_density(): void
    {
        $spool = new Spool(['diameter' => 1.75, 'density' => 1.24]);

        // A metre of 1.75 mm PLA weighs about three grams.
        $this->assertSame(2.98, $spool->gramsFor(1000.0));
        $this->assertSame(335.3, $spool->millimetresFor(1.0));
        $this->assertEqualsWithDelta(1000.0, $spool->millimetresFor($spool->gramsFor(1000.0)), 2.0);

        $thick = new Spool(['diameter' => 2.85, 'density' => 1.27]);
        $this->assertSame(8.1, $thick->gramsFor(1000.0));
    }

    public function test_remaining_never_drops_below_zero(): void
    {
        $this->assertSame(250.5, (new Spool(['weight' => 1000, 'used' => 749.5]))->remaining());
        $this->assertSame(0.0, (new Spool(['weight' => 1000, 'used' => 1020]))->remaining());
    }
}
