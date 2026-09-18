# PrintPi web app

The Laravel API and the Vue dashboard. The daemon in `../daemon` does the talking to the printer,
this part only reads and publishes through Redis.

```bash
composer install && npm install
cp .env.example .env && php artisan key:generate
php artisan migrate
php artisan serve        # http://localhost:8000
npm run dev              # Vite with HMR
php artisan test --compact
npm test                 # node --test for the pure JS modules
```

Everything else, including the Redis contract with the daemon, is in
[docs/development.md](../docs/development.md).
