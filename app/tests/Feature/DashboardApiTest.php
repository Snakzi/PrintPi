<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class DashboardApiTest extends TestCase
{
    use RefreshDatabase;

    private User $user;

    protected function setUp(): void
    {
        parent::setUp();
        $this->user = User::factory()->create();
        $this->actingAs($this->user);
    }

    public function test_show_returns_the_default_layout_and_widget_catalog(): void
    {
        $this->getJson(route('dashboard.show'))
            ->assertOk()
            ->assertJsonPath('customized', false)
            ->assertJsonPath('columns', 12)
            ->assertJsonPath('layout.0.type', 'temperatures')
            ->assertJsonPath('widgets.camera.title', 'Camera')
            ->assertJsonStructure(['layout' => [['i', 'type', 'x', 'y', 'w', 'h']], 'widgets' => ['system' => ['title', 'description', 'w', 'h', 'min_w', 'min_h', 'needs_connection']]]);
    }

    public function test_update_stores_the_layout_for_the_user(): void
    {
        $layout = [
            ['i' => 'a', 'type' => 'camera', 'x' => 0, 'y' => 0, 'w' => 6, 'h' => 8, 'extra' => 'dropped'],
            ['i' => 'b', 'type' => 'system', 'x' => 6, 'y' => 0, 'w' => 3, 'h' => 5],
        ];

        $this->putJson(route('dashboard.update'), ['layout' => $layout])
            ->assertOk()
            ->assertJsonPath('customized', true)
            ->assertJsonCount(2, 'layout')
            ->assertJsonMissingPath('layout.0.extra');

        $this->getJson(route('dashboard.show'))
            ->assertJsonPath('customized', true)
            ->assertJsonPath('layout.1.type', 'system');
        $this->assertSame('camera', $this->user->fresh()->dashboard[0]['type']);
    }

    public function test_update_rejects_unknown_duplicate_and_overflowing_widgets(): void
    {
        $this->putJson(route('dashboard.update'), ['layout' => [
            ['i' => 'a', 'type' => 'unknown', 'x' => 0, 'y' => 0, 'w' => 3, 'h' => 3],
            ['i' => 'b', 'type' => 'camera', 'x' => 0, 'y' => 0, 'w' => 3, 'h' => 3],
            ['i' => 'c', 'type' => 'camera', 'x' => 0, 'y' => 0, 'w' => 3, 'h' => 3],
            ['i' => 'd', 'type' => 'system', 'x' => 10, 'y' => 0, 'w' => 6, 'h' => 3],
        ]])
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['layout.0.type', 'layout.1.type', 'layout.3.w']);

        $this->assertNull($this->user->fresh()->dashboard);
    }

    public function test_an_empty_layout_is_allowed(): void
    {
        $this->putJson(route('dashboard.update'), ['layout' => []])
            ->assertOk()
            ->assertJsonCount(0, 'layout');
    }

    public function test_destroy_restores_the_default_layout(): void
    {
        $this->user->forceFill(['dashboard' => [['i' => 'a', 'type' => 'camera', 'x' => 0, 'y' => 0, 'w' => 6, 'h' => 8]]])->save();

        $this->deleteJson(route('dashboard.reset'))
            ->assertOk()
            ->assertJsonPath('customized', false)
            ->assertJsonPath('layout.0.type', 'temperatures');

        $this->assertNull($this->user->fresh()->dashboard);
    }
}
