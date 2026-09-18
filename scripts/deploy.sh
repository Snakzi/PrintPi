#!/usr/bin/env bash
# Build the frontend, sync this checkout to the Pi as releases/dev and run the installer there.
#
#   scripts/deploy.sh                      -> pi@printer.local
#   PI=pi@192.168.1.50 scripts/deploy.sh
#   SKIP_BUILD=1 scripts/deploy.sh         reuse the last frontend build
#   SSH_KEY=~/.ssh/id_pi scripts/deploy.sh  key to use when it is not in the agent or ssh config
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PI="${PI:-pi@printer.local}"
PRINTPI_HOME="${PRINTPI_HOME:-/opt/printpi}"
DEST="${PRINTPI_DEST:-$PRINTPI_HOME/releases/dev}"
SSH="ssh${SSH_KEY:+ -i $SSH_KEY}"

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
    echo "==> Building frontend"
    (cd "$ROOT/app" && npm run build --silent)
fi

echo "==> Syncing to $PI:$DEST"
$SSH -t "$PI" "sudo mkdir -p '$DEST' && sudo chown \"\$(id -un)\" '$DEST'"
# --no-perms keeps the group write bits install.sh gives www-data on storage, database and
# bootstrap/cache; with -a alone a sync resets them to the Mac's modes and the web app cannot
# write its SQLite database until the installer has run.
# Files git excludes only on this machine (.git/info/exclude) never leave it.
LOCAL_EXCLUDES="$(git -C "$ROOT" ls-files --others --ignored --directory --exclude-from="$ROOT/.git/info/exclude" 2>/dev/null | sed 's|^|/|' || true)"
rsync -az --no-perms --delete --exclude-from="$ROOT/scripts/deploy.exclude" --exclude-from=<(printf '%s\n' "$LOCAL_EXCLUDES") -e "$SSH" "$ROOT/" "$PI:$DEST/"

echo "==> Installing"
$SSH -t "$PI" "sudo PRINTPI_HOME='$PRINTPI_HOME' '$DEST/deploy/install.sh'"
