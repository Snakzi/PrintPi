#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "$ROOT/VERSION")"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] || { echo "invalid VERSION" >&2; exit 2; }
PRINTPI_SIGNING_KEY="${PRINTPI_SIGNING_KEY:-$HOME/.minisign/printpi.key}"
command -v minisign >/dev/null || { echo "Install minisign; see deploy/README-updates.md" >&2; exit 1; }
[[ -f "$PRINTPI_SIGNING_KEY" ]] || { echo "Signing key missing; see deploy/README-updates.md" >&2; exit 1; }
if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
    echo "Warning: working tree is dirty; the release includes local changes." >&2
fi
if [[ "${SKIP_BUILD:-0}" != 1 ]]; then
    (cd "$ROOT/app" && npm run build --silent)
fi
STAGE="$ROOT/dist/stage/printpi-$VERSION"
rm -rf -- "$STAGE"
mkdir -p "$STAGE"
# A release is what git tracks, minus tests and CI, plus the frontend build. Local files
# that are not in git never end up in a package.
git -C "$ROOT" ls-files -z -- . ':!app/tests' ':!daemon/tests' ':!*.test.js' ':!.github' | rsync -a --files-from=- --from0 "$ROOT/" "$STAGE/"
rsync -a "$ROOT/app/public/build/" "$STAGE/app/public/build/"
(cd "$STAGE/app" && composer install --no-dev --optimize-autoloader --no-interaction --quiet)
cp "$ROOT/VERSION" "$STAGE/VERSION"
TARBALL="$ROOT/dist/printpi-$VERSION.tar.gz"
# macOS resource forks and extended attributes do not belong in Linux releases.
# macOS xattrs would become pax headers that GNU tar on the Pi warns about for every file.
COPYFILE_DISABLE=1 tar --no-xattrs --no-mac-metadata -czf "$TARBALL" -C "$ROOT/dist/stage" "printpi-$VERSION"
SHA256="$(shasum -a 256 "$TARBALL")"
SHA256="${SHA256%% *}"
minisign -S -s "$PRINTPI_SIGNING_KEY" -m "$TARBALL"
NOTES=""
if [[ "$(git -C "$ROOT" cat-file -t "refs/tags/v$VERSION" 2>/dev/null || true)" == tag ]]; then
    NOTES="$(git -C "$ROOT" tag -l --format='%(contents)' "v$VERSION")"
fi
python3 - "$TARBALL" "$VERSION" "$SHA256" "$NOTES" <<'PY'
import datetime
import json
import pathlib
import sys
archive, version, sha256, notes = sys.argv[1:]
path = pathlib.Path(archive)
entry = dict(version=version, date=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d'),
             file=path.name, sha256=sha256, size=path.stat().st_size, notes=notes)
path.with_name(f'printpi-{version}.json').write_text(json.dumps(entry, indent=2) + '\n')
PY
printf '%s\n' "$TARBALL" "$TARBALL.minisig" "$ROOT/dist/printpi-$VERSION.json"
