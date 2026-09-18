<?php

namespace App\Services;

/**
 * The printer profiles from config/printers.php.
 */
class PrinterCatalog
{
    /**
     * @return list<array<string, mixed>>
     */
    public function all(): array
    {
        return array_values(array_map(
            fn (array $printer): array => $printer + ['image' => $this->image($printer)],
            config('printers.models', []),
        ));
    }

    /**
     * A photo in public/images/printers/<id>.png wins over the drawing for the type.
     *
     * @param  array<string, mixed>  $printer
     */
    private function image(array $printer): string
    {
        $photo = "images/printers/{$printer['id']}.png";

        return file_exists(public_path($photo)) ? "/{$photo}" : "/images/printers/{$printer['type']}.svg";
    }

    /**
     * @return array<string, mixed>|null
     */
    public function find(string $id): ?array
    {
        foreach ($this->all() as $printer) {
            if ($printer['id'] === $id) {
                return $printer;
            }
        }

        return null;
    }

    /**
     * @return list<string>
     */
    public function supportedIds(): array
    {
        return array_values(array_map(
            static fn (array $printer): string => $printer['id'],
            array_filter($this->all(), static fn (array $printer): bool => (bool) $printer['supported']),
        ));
    }
}
