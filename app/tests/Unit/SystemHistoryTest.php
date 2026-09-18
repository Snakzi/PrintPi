<?php

namespace Tests\Unit;

use App\Services\PrinterBridge;
use PHPUnit\Framework\TestCase;

class SystemHistoryTest extends TestCase
{
    public function test_points_older_than_the_span_and_malformed_entries_are_dropped(): void
    {
        $now = 1758000000;
        $entries = [
            json_encode([$now - 90000, 10.0, 30.0]),  // a day and more ago
            json_encode([$now - 60, 12.5, 41.0]),
            json_encode([$now - 30, null, '41.2']),
            'not json',
            json_encode(['t' => $now]),
            json_encode([$now, 1.0]),
        ];

        $this->assertSame(
            ['interval' => 30, 'points' => [[$now - 60, 12.5, 41.0], [$now - 30, null, 41.2]]],
            PrinterBridge::systemHistoryFrom($entries, (float) $now),
        );
    }
}
