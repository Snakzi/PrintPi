<?php

namespace App\Services;

/**
 * Reads the slicer comments of a G-code file: estimated time, filament, temperatures.
 *
 * PrusaSlicer, SuperSlicer and OrcaSlicer write their summary at the end of the
 * file, Cura at the start, so only the first and last 64 KB are inspected. A
 * multi-extruder file lists one filament amount per extruder; they are summed.
 */
class GcodeMetadata
{
    private const int WINDOW = 65536;

    /**
     * @return array{slicer: ?string, estimated_seconds: ?int, filament_mm: ?float, filament_g: ?float, filament_type: ?string, layer_height: ?float, nozzle_temperature: ?int, bed_temperature: ?int}
     */
    public function fromPath(string $path): array
    {
        $handle = @fopen($path, 'rb');
        if ($handle === false) {
            return $this->parse('');
        }

        $head = (string) fread($handle, self::WINDOW);
        $tail = '';
        $size = filesize($path) ?: 0;
        if ($size > self::WINDOW) {
            fseek($handle, -self::WINDOW, SEEK_END);
            $tail = (string) fread($handle, self::WINDOW);
        }
        fclose($handle);

        return $this->parse($head."\n".$tail);
    }

    /**
     * @return array{slicer: ?string, estimated_seconds: ?int, filament_mm: ?float, filament_g: ?float, filament_type: ?string, layer_height: ?float, nozzle_temperature: ?int, bed_temperature: ?int}
     */
    public function parse(string $text): array
    {
        return [
            'slicer' => $this->slicer($text),
            'estimated_seconds' => $this->estimatedSeconds($text),
            'filament_mm' => $this->filamentMillimetres($text),
            'filament_g' => $this->rounded($this->sum($text, '/^;\s*(?:total )?filament used \[g\]\s*=\s*([\d.,\h]+)/mi')),
            'filament_type' => $this->filamentType($text),
            'layer_height' => $this->float($text, '/^;\s*layer_height\s*=\s*([\d.]+)/mi')
                ?? $this->float($text, '/^;\s*Layer height:\s*([\d.]+)/mi'),
            'nozzle_temperature' => $this->int($text, '/^;\s*temperature\s*=\s*(\d+)/mi')
                ?? $this->int($text, '/^M10[49]\s+S(\d+)/mi'),
            'bed_temperature' => $this->int($text, '/^;\s*bed_temperature\s*=\s*(\d+)/mi')
                ?? $this->int($text, '/^M1[49]0\s+S(\d+)/mi'),
        ];
    }

    private function slicer(string $text): ?string
    {
        if (preg_match('/^;\s*generated (?:by|with) (.+?)(?:\s+on\s+.*)?$/mi', $text, $match) === 1) {
            return trim($match[1]);
        }

        return null;
    }

    private function estimatedSeconds(string $text): ?int
    {
        if (preg_match('/^;\s*estimated printing time.*?=\s*(.+)$/mi', $text, $match) === 1) {
            return $this->durationToSeconds(trim($match[1]));
        }
        if (preg_match('/^;TIME:(\d+)/m', $text, $match) === 1) {
            return (int) $match[1];
        }

        return null;
    }

    private function durationToSeconds(string $duration): ?int
    {
        if (preg_match_all('/(\d+)\s*([dhms])/', $duration, $matches, PREG_SET_ORDER) === 0) {
            return null;
        }
        $factors = ['d' => 86400, 'h' => 3600, 'm' => 60, 's' => 1];
        $seconds = 0;
        foreach ($matches as $match) {
            $seconds += (int) $match[1] * $factors[$match[2]];
        }

        return $seconds;
    }

    private function filamentMillimetres(string $text): ?float
    {
        $millimetres = $this->sum($text, '/^;\s*filament used \[mm\]\s*=\s*([\d.,\h]+)/mi');
        if ($millimetres !== null) {
            return $this->rounded($millimetres);
        }
        $metres = $this->sum($text, '/^;Filament used:\s*((?:[\d.]+\h*m,?\h*)+)/mi');

        return $metres !== null ? round($metres * 1000, 1) : null;
    }

    /**
     * The material of the first extruder; PrusaSlicer and Orca list one per extruder separated by semicolons.
     */
    private function filamentType(string $text): ?string
    {
        if (preg_match('/^;\s*filament_type\s*=\s*([^;\r\n]+)/mi', $text, $match) !== 1) {
            return null;
        }
        $type = trim($match[1]);

        return $type !== '' ? $type : null;
    }

    /**
     * The sum of the numbers in the first line matching the pattern, one per extruder.
     */
    private function sum(string $text, string $pattern): ?float
    {
        if (preg_match($pattern, $text, $match) !== 1 || preg_match_all('/[\d.]+/', $match[1], $numbers) === 0) {
            return null;
        }

        return array_sum(array_map(floatval(...), $numbers[0]));
    }

    private function rounded(?float $value): ?float
    {
        return $value === null ? null : round($value, 2);
    }

    private function float(string $text, string $pattern): ?float
    {
        return preg_match($pattern, $text, $match) === 1 ? (float) $match[1] : null;
    }

    private function int(string $text, string $pattern): ?int
    {
        return preg_match($pattern, $text, $match) === 1 ? (int) $match[1] : null;
    }
}
