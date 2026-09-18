<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ApiKeyApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_the_key_is_shown_and_regenerated_for_the_signed_in_user(): void
    {
        $user = User::factory()->create(['api_key' => null]);
        $this->actingAs($user);

        $this->getJson(route('api-key.show'))->assertOk()->assertJsonPath('api_key', null);

        $first = $this->postJson(route('api-key.store'))->assertOk()->json('api_key');
        $this->assertSame(32, strlen($first));
        $this->assertSame($first, $user->fresh()->api_key);

        $second = $this->postJson(route('api-key.store'))->assertOk()->json('api_key');
        $this->assertNotSame($first, $second);
        $this->getJson(route('api-key.show'))->assertJsonPath('api_key', $second);
    }

    public function test_the_key_needs_a_login_and_never_leaks_through_the_session(): void
    {
        $user = User::factory()->create(['api_key' => 'SECRET-KEY-SECRET-KEY-SECRET-KEY']);

        $this->getJson(route('api-key.show'))->assertUnauthorized();
        $this->actingAs($user)->getJson(route('session.show'))->assertOk()->assertJsonMissing(['api_key' => 'SECRET-KEY-SECRET-KEY-SECRET-KEY']);
        $this->assertArrayNotHasKey('api_key', $user->toArray());
    }
}
