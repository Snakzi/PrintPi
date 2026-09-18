<?php

namespace App\Http\Requests;

use App\Services\Dashboard;
use Closure;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;
use Illuminate\Validation\Validator;

class UpdateDashboardRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /**
     * @return array<string, list<mixed>>
     */
    public function rules(): array
    {
        $dashboard = app(Dashboard::class);
        $columns = $dashboard->columns();

        return [
            'layout' => ['present', 'array', 'max:30'],
            'layout.*.i' => ['required', 'string', 'max:40', 'distinct'],
            'layout.*.type' => ['required', 'string', Rule::in($dashboard->types()), 'distinct'],
            'layout.*.x' => ['required', 'integer', 'min:0', 'max:'.($columns - 1)],
            'layout.*.y' => ['required', 'integer', 'min:0', 'max:500'],
            'layout.*.w' => ['required', 'integer', 'min:1', 'max:'.$columns],
            'layout.*.h' => ['required', 'integer', 'min:1', 'max:60'],
        ];
    }

    /**
     * @return list<Closure>
     */
    public function after(): array
    {
        $columns = app(Dashboard::class)->columns();

        return [
            function (Validator $validator) use ($columns): void {
                foreach ($this->input('layout', []) as $index => $item) {
                    if (is_array($item) && (int) ($item['x'] ?? 0) + (int) ($item['w'] ?? 0) > $columns) {
                        $validator->errors()->add("layout.{$index}.w", "The widget must fit into {$columns} columns.");
                    }
                }
            },
        ];
    }
}
