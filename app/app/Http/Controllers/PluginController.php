<?php

namespace App\Http\Controllers;

use App\Http\Requests\InstallPluginRequest;
use App\Http\Requests\PluginActionRequest;
use App\Services\PluginManager;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

class PluginController extends Controller
{
    public function __construct(private readonly PluginManager $plugins) {}

    public function index(): JsonResponse
    {
        return response()->json(['data' => $this->plugins->all()]);
    }

    public function store(InstallPluginRequest $request): JsonResponse
    {
        $plugin = $request->filled('url')
            ? $this->plugins->installFromGit($request->validated('url'))
            : $this->plugins->install($request->validated('id'));

        return response()->json($plugin, 201);
    }

    public function update(Request $request, string $plugin): JsonResponse
    {
        $validated = $request->validate(['enabled' => ['required', 'boolean']]);

        return response()->json($this->plugins->setEnabled($plugin, $validated['enabled']));
    }

    public function updateSettings(Request $request, string $plugin): JsonResponse
    {
        return response()->json($this->plugins->updateSettings($plugin, $request->all()));
    }

    public function action(PluginActionRequest $request, string $plugin): JsonResponse
    {
        $this->plugins->action($plugin, $request->validated('action'), $request->validated('value'));

        return response()->json(['queued' => true], 202);
    }

    public function upgrade(string $plugin): JsonResponse
    {
        return response()->json($this->plugins->upgrade($plugin));
    }

    public function destroy(string $plugin): Response
    {
        $this->plugins->uninstall($plugin);

        return response()->noContent();
    }
}
