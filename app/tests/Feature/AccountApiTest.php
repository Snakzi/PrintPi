<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

class AccountApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_username_and_email_can_be_changed(): void
    {
        $user = User::factory()->create(['username' => 'alice', 'email' => 'alice@example.com']);

        $this->actingAs($user)
            ->putJson(route('account.update'), ['username' => 'bob', 'email' => 'Bob@Example.com'])
            ->assertOk()
            ->assertJsonPath('user.username', 'bob')
            ->assertJsonPath('user.name', 'bob')
            ->assertJsonPath('user.email', 'bob@example.com');

        $this->assertSame('bob', $user->fresh()->name);
    }

    public function test_profile_rules_reject_taken_names_and_bad_input(): void
    {
        User::factory()->create(['username' => 'other', 'email' => 'other@example.com']);
        $user = User::factory()->create(['username' => 'alice', 'email' => 'alice@example.com']);
        $this->actingAs($user);

        $this->putJson(route('account.update'), ['username' => 'other', 'email' => 'alice@example.com'])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('username');
        $this->putJson(route('account.update'), ['username' => 'alice', 'email' => 'other@example.com'])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('email');
        $this->putJson(route('account.update'), ['username' => 'a b', 'email' => 'not-an-email'])
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['username', 'email']);
        // Keeping the own values is fine.
        $this->putJson(route('account.update'), ['username' => 'alice', 'email' => 'alice@example.com'])->assertOk();
    }

    public function test_password_change_needs_the_current_password(): void
    {
        $user = User::factory()->create(['password' => 'old-password-1']);
        $this->actingAs($user);

        $this->putJson(route('account.password'), ['current_password' => 'wrong', 'password' => 'new-password-1', 'password_confirmation' => 'new-password-1'])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('current_password');
        $this->putJson(route('account.password'), ['current_password' => 'old-password-1', 'password' => 'short', 'password_confirmation' => 'short'])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('password');
        $this->putJson(route('account.password'), ['current_password' => 'old-password-1', 'password' => 'new-password-1', 'password_confirmation' => 'other'])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('password');

        $this->putJson(route('account.password'), ['current_password' => 'old-password-1', 'password' => 'new-password-1', 'password_confirmation' => 'new-password-1'])
            ->assertNoContent();
        $this->assertTrue(Hash::check('new-password-1', $user->fresh()->password));
    }

    public function test_the_account_endpoints_need_a_login(): void
    {
        $this->putJson(route('account.update'), ['username' => 'x', 'email' => 'x@example.com'])->assertUnauthorized();
        $this->putJson(route('account.password'), [])->assertUnauthorized();
    }
}
