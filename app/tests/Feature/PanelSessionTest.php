<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class PanelSessionTest extends TestCase
{
    use RefreshDatabase;

    public function test_the_kiosk_signs_in_the_first_user_with_the_token_from_loopback(): void
    {
        config(['printpi.panel_token' => 'kiosk-secret']);
        $first = User::factory()->create();
        User::factory()->create();

        $this->get(route('panel.login', ['token' => 'kiosk-secret']), ['REMOTE_ADDR' => '127.0.0.1'])
            ->assertRedirect('/panel');
        $this->assertAuthenticatedAs($first);
    }

    public function test_a_wrong_token_or_another_host_is_refused(): void
    {
        config(['printpi.panel_token' => 'kiosk-secret']);
        User::factory()->create();

        $this->get(route('panel.login', ['token' => 'wrong']), ['REMOTE_ADDR' => '127.0.0.1'])->assertForbidden();
        $this->get(route('panel.login'), ['REMOTE_ADDR' => '127.0.0.1'])->assertForbidden();
        $this->get(route('panel.login', ['token' => 'kiosk-secret']), ['REMOTE_ADDR' => '192.168.1.5'])->assertForbidden();
        $this->assertGuest();
    }

    public function test_without_a_configured_token_the_endpoint_does_not_exist(): void
    {
        config(['printpi.panel_token' => null]);
        User::factory()->create();

        $this->get(route('panel.login', ['token' => 'anything']), ['REMOTE_ADDR' => '127.0.0.1'])->assertNotFound();
        $this->assertGuest();
    }
}
