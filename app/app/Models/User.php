<?php

namespace App\Models;

// use Illuminate\Contracts\Auth\MustVerifyEmail;
use Database\Factories\UserFactory;
use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Hidden;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Illuminate\Support\Str;
use Laravel\Passkeys\Contracts\PasskeyUser;
use Laravel\Passkeys\PasskeyAuthenticatable;

#[Fillable(['name', 'username', 'email', 'password', 'api_key', 'dashboard'])]
#[Hidden(['password', 'remember_token', 'api_key'])]
class User extends Authenticatable implements PasskeyUser
{
    /** @use HasFactory<UserFactory> */
    use HasFactory, Notifiable, PasskeyAuthenticatable;

    /**
     * A fresh key for the API slicers upload through.
     */
    public static function newApiKey(): string
    {
        return Str::random(32);
    }

    public function regenerateApiKey(): string
    {
        $this->forceFill(['api_key' => self::newApiKey()])->save();

        return $this->api_key;
    }

    /**
     * The account name an authenticator shows under the passkey; users sign in
     * with the username here, not the email the package would pick.
     */
    public function getPasskeyUsername(): string
    {
        return $this->username;
    }

    /**
     * Get the attributes that should be cast.
     *
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'email_verified_at' => 'datetime',
            'password' => 'hashed',
            'dashboard' => 'array',
        ];
    }
}
