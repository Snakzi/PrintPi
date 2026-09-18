<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Auth;
use Tests\TestCase;

class SessionApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_session_reports_setup_and_authentication_state(): void
    {
        $this->getJson(route('session.show'))
            ->assertOk()
            ->assertExactJson(['setup_complete' => false, 'authenticated' => false, 'passkeys' => false, 'user' => null, 'system_control' => false]);

        $user = User::factory()->create(['username' => 'alice']);

        $this->getJson(route('session.show'))->assertJsonPath('setup_complete', true)->assertJsonPath('authenticated', false);
        $this->actingAs($user)->getJson(route('session.show'))->assertJsonPath('user.username', 'alice');
    }

    public function test_login_and_logout(): void
    {
        User::factory()->create(['username' => 'alice', 'password' => 'secret-1234']);

        $this->postJson(route('session.login'), ['username' => 'alice', 'password' => 'wrong'])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('username');
        $this->assertGuest();

        $this->postJson(route('session.login'), ['username' => 'alice', 'password' => 'secret-1234'])
            ->assertOk()
            ->assertJsonPath('user.username', 'alice');
        $this->assertAuthenticated();

        $this->postJson(route('session.logout'))->assertNoContent();
        $this->assertGuest();
    }

    public function test_login_can_remember_the_user_beyond_the_session(): void
    {
        User::factory()->create(['username' => 'alice', 'password' => 'secret-1234']);
        $recaller = Auth::guard('web')->getRecallerName();

        $this->postJson(route('session.login'), ['username' => 'alice', 'password' => 'secret-1234'])
            ->assertOk()
            ->assertCookieMissing($recaller);

        $this->postJson(route('session.logout'))->assertNoContent();

        $this->postJson(route('session.login'), ['username' => 'alice', 'password' => 'secret-1234', 'remember' => true])
            ->assertOk()
            ->assertCookieNotExpired($recaller);
    }

    public function test_login_ignores_the_case_of_the_username(): void
    {
        User::factory()->create(['username' => 'Alice', 'password' => 'secret-1234']);

        $this->postJson(route('session.login'), ['username' => 'alice', 'password' => 'secret-1234'])
            ->assertOk()
            ->assertJsonPath('user.username', 'Alice');
        $this->postJson(route('session.logout'))->assertNoContent();
        $this->postJson(route('session.login'), ['username' => 'ALICE', 'password' => 'secret-1234'])
            ->assertOk()
            ->assertJsonPath('user.username', 'Alice');
    }

    public function test_login_accepts_the_email_address_too(): void
    {
        User::factory()->create(['username' => 'alice', 'email' => 'alice@example.com', 'password' => 'secret-1234']);

        $this->postJson(route('session.login'), ['username' => 'Alice@Example.com', 'password' => 'secret-1234'])
            ->assertOk()
            ->assertJsonPath('user.email', 'alice@example.com');
        $this->assertAuthenticated();
    }

    public function test_api_requires_a_session(): void
    {
        $this->getJson(route('printer.state'))->assertUnauthorized();
        $this->getJson(route('files.index'))->assertUnauthorized();
        $this->getJson(route('settings.show'))->assertUnauthorized();
        $this->getJson(route('camera.show'))->assertUnauthorized();
        $this->postJson(route('system.reboot'))->assertUnauthorized();
        $this->postJson(route('system.restart-web'))->assertUnauthorized();
    }
}
