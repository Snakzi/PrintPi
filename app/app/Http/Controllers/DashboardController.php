<?php

namespace App\Http\Controllers;

use App\Http\Requests\UpdateDashboardRequest;
use App\Services\Dashboard;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class DashboardController extends Controller
{
    public function __construct(private readonly Dashboard $dashboard) {}

    public function show(Request $request): JsonResponse
    {
        $user = $request->user();

        return response()->json([
            'layout' => $this->dashboard->layoutFor($user),
            'customized' => $user->dashboard !== null,
            'widgets' => $this->dashboard->widgets(),
            'columns' => $this->dashboard->columns(),
        ]);
    }

    public function update(UpdateDashboardRequest $request): JsonResponse
    {
        $layout = array_values($request->validated('layout'));
        $user = $request->user();
        $user->dashboard = $layout;
        $user->save();

        return response()->json(['layout' => $layout, 'customized' => true]);
    }

    /**
     * Forget the user's layout and go back to the default.
     */
    public function destroy(Request $request): JsonResponse
    {
        $user = $request->user();
        $user->dashboard = null;
        $user->save();

        return response()->json(['layout' => $this->dashboard->defaultLayout(), 'customized' => false]);
    }
}
