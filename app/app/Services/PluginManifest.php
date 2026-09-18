<?php

namespace App\Services;

use App\Exceptions\PluginException;
use Illuminate\Support\Facades\Validator;
use Illuminate\Validation\Rule;
use JsonException;

/**
 * The plugin.json of a plugin: identity, the settings form and the dashboard controls.
 *
 * Settings fields are {key, label, type, default?, min?, max?, options?} with a type of
 * string, password, text (multi-line), integer, number, boolean, select or color; select
 * needs options [{value, label}].
 * Controls are {key, label, type, action, actions?, min?, max?, step?, unit?, options?} with
 * a type of toggle, color, range, button, select or text. The action goes to the daemon part
 * of the plugin and the control's current value is read from the plugin's status under key;
 * actions lists further action names the control may send.
 * Two types are a whole section on the plugin page instead of a row: for mesh the status
 * under key is a bed mesh report and the action probes the bed; for devices the status is
 * {scanning, error, found, devices}, the action scans the network and the actions add,
 * remove, turn_on and turn_off take a device id. A devices control also shows on the
 * dashboard as one switch per added device.
 */
final class PluginManifest
{
    public const string ID_PATTERN = '/^[a-z0-9][a-z0-9_-]{0,63}$/';

    public const string KEY_PATTERN = '/^[a-z][a-z0-9_]{0,63}$/';

    private const array FIELD_TYPES = ['string', 'password', 'text', 'integer', 'number', 'boolean', 'select', 'color'];

    private const array CONTROL_TYPES = ['toggle', 'color', 'range', 'button', 'select', 'text', 'mesh', 'devices'];

    /**
     * @param  list<array<string, mixed>>  $settings
     * @param  list<array<string, mixed>>  $controls
     */
    private function __construct(
        public readonly string $id,
        public readonly string $name,
        public readonly string $version,
        public readonly string $description,
        public readonly ?string $author,
        public readonly ?string $homepage,
        public readonly ?string $icon,
        public readonly bool $daemon,
        public readonly array $settings,
        public readonly array $controls,
    ) {}

    public static function fromDirectory(string $path): self
    {
        $file = rtrim($path, '/').'/plugin.json';
        if (! is_file($file)) {
            throw new PluginException('plugin.json is missing.');
        }
        try {
            $data = json_decode((string) file_get_contents($file), true, 32, JSON_THROW_ON_ERROR);
        } catch (JsonException $exception) {
            throw new PluginException('plugin.json is not valid JSON: '.$exception->getMessage());
        }
        if (! is_array($data)) {
            throw new PluginException('plugin.json must contain an object.');
        }

        return self::fromArray($data);
    }

    /**
     * @param  array<string, mixed>  $data
     */
    public static function fromArray(array $data): self
    {
        $validator = Validator::make($data, [
            'id' => ['required', 'string', 'regex:'.self::ID_PATTERN],
            'name' => ['required', 'string', 'max:100'],
            'version' => ['required', 'string', 'max:50'],
            'description' => ['nullable', 'string', 'max:500'],
            'author' => ['nullable', 'string', 'max:100'],
            'homepage' => ['nullable', 'string', 'url', 'max:500'],
            'icon' => ['nullable', 'string', 'max:50'],
            'daemon' => ['nullable', 'boolean'],
            'settings' => ['nullable', 'array'],
            'settings.*.key' => ['required', 'string', 'regex:'.self::KEY_PATTERN, 'distinct'],
            'settings.*.label' => ['required', 'string', 'max:100'],
            'settings.*.type' => ['required', Rule::in(self::FIELD_TYPES)],
            'settings.*.min' => ['nullable', 'numeric'],
            'settings.*.max' => ['nullable', 'numeric'],
            'settings.*.options' => ['required_if:settings.*.type,select', 'array', 'min:1'],
            'settings.*.options.*.value' => ['required'],
            'settings.*.options.*.label' => ['required', 'string', 'max:100'],
            'controls' => ['nullable', 'array'],
            'controls.*.key' => ['required', 'string', 'regex:'.self::KEY_PATTERN, 'distinct'],
            'controls.*.label' => ['required', 'string', 'max:100'],
            'controls.*.type' => ['required', Rule::in(self::CONTROL_TYPES)],
            'controls.*.action' => ['required', 'string', 'regex:'.self::KEY_PATTERN],
            'controls.*.actions' => ['nullable', 'array'],
            'controls.*.actions.*' => ['required', 'string', 'regex:'.self::KEY_PATTERN],
            'controls.*.options' => ['required_if:controls.*.type,select', 'array', 'min:1'],
            'controls.*.options.*.value' => ['required'],
            'controls.*.options.*.label' => ['required', 'string', 'max:100'],
        ]);
        if ($validator->fails()) {
            throw new PluginException('Invalid plugin.json: '.$validator->errors()->first());
        }

        return new self(
            id: $data['id'],
            name: $data['name'],
            version: $data['version'],
            description: (string) ($data['description'] ?? ''),
            author: $data['author'] ?? null,
            homepage: $data['homepage'] ?? null,
            icon: $data['icon'] ?? null,
            daemon: (bool) ($data['daemon'] ?? true),
            settings: array_values($data['settings'] ?? []),
            controls: array_values($data['controls'] ?? []),
        );
    }

    /**
     * @return array<string, mixed>
     */
    public function defaults(): array
    {
        $defaults = [];
        foreach ($this->settings as $field) {
            $defaults[$field['key']] = array_key_exists('default', $field)
                ? $this->cast($field, $field['default'])
                : match ($field['type']) {
                    'integer' => (int) ($field['min'] ?? 0),
                    'number' => (float) ($field['min'] ?? 0),
                    'boolean' => false,
                    'select' => $field['options'][0]['value'],
                    'color' => '#ffffff',
                    default => '',
                };
        }

        return $defaults;
    }

    /**
     * Validation rules for a settings update; every field is optional so partial updates work.
     *
     * @return array<string, list<mixed>>
     */
    public function rules(): array
    {
        $rules = [];
        foreach ($this->settings as $field) {
            $rules[$field['key']] = match ($field['type']) {
                'integer' => ['sometimes', 'required', 'integer', ...$this->bounds($field)],
                'number' => ['sometimes', 'required', 'numeric', ...$this->bounds($field)],
                'boolean' => ['sometimes', 'required', 'boolean'],
                'select' => ['sometimes', 'required', Rule::in(array_column($field['options'], 'value'))],
                'color' => ['sometimes', 'required', 'string', 'regex:/^#[0-9a-fA-F]{6}$/'],
                'text' => ['sometimes', 'nullable', 'string', 'max:5000'],
                default => ['sometimes', 'nullable', 'string', 'max:1000'],
            };
        }

        return $rules;
    }

    /**
     * Keep only known keys, cast to the type the field declares.
     *
     * @param  array<string, mixed>  $values
     * @return array<string, mixed>
     */
    public function normalize(array $values): array
    {
        $normalized = [];
        foreach ($this->settings as $field) {
            if (array_key_exists($field['key'], $values)) {
                $normalized[$field['key']] = $this->cast($field, $values[$field['key']]);
            }
        }

        return $normalized;
    }

    public function hasAction(string $action): bool
    {
        foreach ($this->controls as $control) {
            if ($control['action'] === $action || in_array($action, $control['actions'] ?? [], true)) {
                return true;
            }
        }

        return false;
    }

    /**
     * @return array<string, mixed>
     */
    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'version' => $this->version,
            'description' => $this->description,
            'author' => $this->author,
            'homepage' => $this->homepage,
            'icon' => $this->icon,
            'daemon' => $this->daemon,
            'schema' => $this->settings,
            'controls' => $this->controls,
        ];
    }

    /**
     * @param  array<string, mixed>  $field
     */
    private function cast(array $field, mixed $value): mixed
    {
        return match ($field['type']) {
            'integer' => (int) $value,
            'number' => (float) $value,
            'boolean' => filter_var($value, FILTER_VALIDATE_BOOLEAN),
            'select' => $this->optionValue($field, $value),
            default => $value === null ? null : (string) $value,
        };
    }

    /**
     * The option's own value, so "18" from a form comes back as the integer the manifest declares.
     *
     * @param  array<string, mixed>  $field
     */
    private function optionValue(array $field, mixed $value): mixed
    {
        foreach ($field['options'] as $option) {
            if ((string) $option['value'] === (string) $value) {
                return $option['value'];
            }
        }

        return $value;
    }

    /**
     * @param  array<string, mixed>  $field
     * @return list<string>
     */
    private function bounds(array $field): array
    {
        $bounds = [];
        if (isset($field['min'])) {
            $bounds[] = 'min:'.$field['min'];
        }
        if (isset($field['max'])) {
            $bounds[] = 'max:'.$field['max'];
        }

        return $bounds;
    }
}
