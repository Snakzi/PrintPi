<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Passkeys\Actions\StorePasskey;
use Laravel\Passkeys\Actions\VerifyPasskey;
use Laravel\Passkeys\Exceptions\InvalidPasskeyException;
use Laravel\Passkeys\Passkey;
use ParagonIE\ConstantTime\Base64UrlSafe;
use Tests\TestCase;

class PasskeyApiTest extends TestCase
{
    use RefreshDatabase;

    private function passkeyFor(User $user, string $name = 'MacBook'): Passkey
    {
        return $user->passkeys()->create(['name' => $name, 'credential_id' => 'cred-'.$name.'-'.$user->id, 'credential' => ['publicKey' => 'test']]);
    }

    /**
     * A credential shaped like what a browser sends, cryptographically meaningless but
     * surviving the package's deserialization; the actions that would check it are mocked.
     *
     * @return array<string, mixed>
     */
    private function credential(bool $attestation): array
    {
        $rawId = random_bytes(16);
        $clientData = json_encode(['type' => $attestation ? 'webauthn.create' : 'webauthn.get', 'challenge' => Base64UrlSafe::encodeUnpadded(random_bytes(32)), 'origin' => 'http://localhost']);
        $authData = hash('sha256', 'localhost', binary: true).chr(0x01).pack('N', 0);
        $response = ['clientDataJSON' => Base64UrlSafe::encodeUnpadded($clientData)];
        if ($attestation) {
            // CBOR {fmt: "none", attStmt: {}, authData: <bytes>}
            $cbor = "\xA3\x63fmt\x64none\x67attStmt\xA0\x68authData\x58".chr(strlen($authData)).$authData;
            $response['attestationObject'] = Base64UrlSafe::encodeUnpadded($cbor);
        } else {
            $response['authenticatorData'] = Base64UrlSafe::encodeUnpadded($authData);
            $response['signature'] = Base64UrlSafe::encodeUnpadded(random_bytes(64));
        }

        return ['id' => Base64UrlSafe::encodeUnpadded($rawId), 'rawId' => Base64UrlSafe::encodeUnpadded($rawId), 'type' => 'public-key', 'response' => $response];
    }

    public function test_registration_options_carry_the_host_as_relying_party_and_stay_in_the_session(): void
    {
        $user = User::factory()->create(['username' => 'alice']);

        $response = $this->actingAs($user)->getJson('http://printpi.local/'.ltrim(parse_url(route('passkeys.options'), PHP_URL_PATH), '/'))->assertOk();

        $response->assertJsonPath('options.rp.id', 'printpi.local')
            ->assertJsonPath('options.user.name', 'alice')
            ->assertJsonPath('options.authenticatorSelection.residentKey', 'required')
            ->assertJsonStructure(['options' => ['challenge', 'pubKeyCredParams']]);
        $this->assertNotNull(session('passkey.registration_options'));
        $this->assertSame(['http://printpi.local'], config('passkeys.allowed_origins'));
    }

    public function test_a_passkey_is_stored_listed_renamed_and_deleted(): void
    {
        $user = User::factory()->create();
        $this->actingAs($user);

        $this->mock(StorePasskey::class, fn ($mock) => $mock->shouldReceive('__invoke')->once()
            ->andReturnUsing(fn () => $this->passkeyFor($user, 'YubiKey')));

        $this->getJson(route('passkeys.options'))->assertOk();
        $this->postJson(route('passkeys.store'), ['name' => 'YubiKey', 'credential' => $this->credential(true)])
            ->assertCreated()
            ->assertJsonPath('data.name', 'YubiKey');

        $id = $this->getJson(route('passkeys.index'))->assertOk()->assertJsonCount(1, 'data')->json('data.0.id');

        $this->putJson(route('passkeys.update', $id), ['name' => 'Blue YubiKey'])->assertOk()->assertJsonPath('data.name', 'Blue YubiKey');
        $this->deleteJson(route('passkeys.destroy', $id))->assertNoContent();
        $this->getJson(route('passkeys.index'))->assertJsonCount(0, 'data');
    }

    public function test_a_registration_without_options_in_the_session_or_with_a_bad_credential_fails(): void
    {
        $user = User::factory()->create();
        $this->actingAs($user);

        $this->postJson(route('passkeys.store'), ['name' => 'X', 'credential' => $this->credential(true)])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('credential');

        $this->mock(StorePasskey::class, fn ($mock) => $mock->shouldReceive('__invoke')->andThrow(InvalidPasskeyException::make()));
        $this->getJson(route('passkeys.options'))->assertOk();
        $this->postJson(route('passkeys.store'), ['name' => 'X', 'credential' => $this->credential(true)])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('credential');
    }

    public function test_only_the_owner_sees_renames_or_deletes_a_passkey(): void
    {
        $owner = User::factory()->create();
        $other = User::factory()->create();
        $passkey = $this->passkeyFor($owner);

        $this->actingAs($other);
        $this->getJson(route('passkeys.index'))->assertJsonCount(0, 'data');
        $this->putJson(route('passkeys.update', $passkey->id), ['name' => 'Mine'])->assertNotFound();
        $this->deleteJson(route('passkeys.destroy', $passkey->id))->assertNotFound();
        $this->assertSame('MacBook', $passkey->fresh()->name);
    }

    public function test_login_options_are_public_and_the_session_reports_registered_passkeys(): void
    {
        $this->getJson(route('session.show'))->assertJsonPath('passkeys', false);

        $this->getJson(route('passkeys.login.options'))
            ->assertOk()
            ->assertJsonStructure(['options' => ['challenge', 'rpId', 'userVerification']])
            ->assertJsonMissingPath('options.allowCredentials.0');
        $this->assertNotNull(session('passkey.verification_options'));

        $this->passkeyFor(User::factory()->create());
        $this->getJson(route('session.show'))->assertJsonPath('passkeys', true);
    }

    public function test_login_with_a_passkey_signs_the_owner_in(): void
    {
        $user = User::factory()->create(['username' => 'alice']);
        $passkey = $this->passkeyFor($user);

        $this->mock(VerifyPasskey::class, fn ($mock) => $mock->shouldReceive('__invoke')->once()->andReturn($passkey));

        $this->getJson(route('passkeys.login.options'))->assertOk();
        $this->postJson(route('passkeys.login'), ['credential' => $this->credential(false)])
            ->assertOk()
            ->assertJsonPath('user.username', 'alice');
        $this->assertAuthenticatedAs($user);
    }

    public function test_login_with_an_unknown_passkey_or_without_options_is_refused(): void
    {
        $this->postJson(route('passkeys.login'), ['credential' => $this->credential(false)])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('credential');

        $this->mock(VerifyPasskey::class, fn ($mock) => $mock->shouldReceive('__invoke')->andThrow(InvalidPasskeyException::make('Passkey not recognized.')));
        $this->getJson(route('passkeys.login.options'))->assertOk();
        $this->postJson(route('passkeys.login'), ['credential' => $this->credential(false)])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('credential');
        $this->assertGuest();
    }

    public function test_managing_passkeys_needs_a_login(): void
    {
        $this->getJson(route('passkeys.index'))->assertUnauthorized();
        $this->getJson(route('passkeys.options'))->assertUnauthorized();
        $this->postJson(route('passkeys.store'), [])->assertUnauthorized();
    }
}
