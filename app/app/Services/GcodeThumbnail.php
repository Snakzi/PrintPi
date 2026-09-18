<?php

namespace App\Services;

/**
 * Extracts the preview image slicers embed as base64 comment blocks:
 *
 *   ; thumbnail begin 313x173 44380
 *   ; iVBORw0KGgo...
 *   ; thumbnail end
 *
 * PrusaSlicer, OrcaSlicer and Cura's thumbnail script all write these at the
 * top of the file; Orca additionally labels JPEG and QOI blocks (thumbnail_JPG,
 * thumbnail_QOI). Only PNG and JPEG are kept because browsers can show them.
 */
class GcodeThumbnail
{
    private const int WINDOW = 4194304;

    private const string PNG_SIGNATURE = "\x89PNG\r\n\x1a\n";

    private const string JPEG_SIGNATURE = "\xFF\xD8\xFF";

    /**
     * @return array{width: int, height: int, extension: string, data: string}|null
     */
    public function fromPath(string $path): ?array
    {
        $handle = @fopen($path, 'rb');
        if ($handle === false) {
            return null;
        }
        $head = (string) fread($handle, self::WINDOW);
        fclose($handle);

        return $this->parse($head);
    }

    /**
     * The largest embedded image, decoded.
     *
     * @return array{width: int, height: int, extension: string, data: string}|null
     */
    public function parse(string $text): ?array
    {
        $pattern = '/^;\s*thumbnail(?:_\w+)?\s+begin\s+(\d+)x(\d+)\s+\d+\s*$(.*?)^;\s*thumbnail(?:_\w+)?\s+end/msi';
        if (preg_match_all($pattern, $text, $blocks, PREG_SET_ORDER) === 0) {
            return null;
        }

        $best = null;
        foreach ($blocks as [, $width, $height, $body]) {
            $data = base64_decode((string) preg_replace('/[^A-Za-z0-9+\/=]/', '', $body), true);
            if ($data === false) {
                continue;
            }
            $extension = $this->extension($data);
            if ($extension === null) {
                continue;
            }
            $area = (int) $width * (int) $height;
            if ($best === null || $area > $best['width'] * $best['height']) {
                $best = ['width' => (int) $width, 'height' => (int) $height, 'extension' => $extension, 'data' => $data];
            }
        }

        return $best;
    }

    private function extension(string $data): ?string
    {
        if (str_starts_with($data, self::PNG_SIGNATURE)) {
            return 'png';
        }
        if (str_starts_with($data, self::JPEG_SIGNATURE)) {
            return 'jpg';
        }

        return null;
    }
}
