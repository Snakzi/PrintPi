#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRINTPI_UPDATE_URL="${PRINTPI_UPDATE_URL:-https://updates.194-164-58-152.sslip.io}"
PRINTPI_UPDATE_URL="${PRINTPI_UPDATE_URL%/}"
PRINTPI_UPDATE_SERVER="${PRINTPI_UPDATE_SERVER:-root@194.164.58.152:/srv/printpi-updates}"
PRINTPI_SSH_KEY="${PRINTPI_SSH_KEY:-}"

merge_manifest() {
    python3 - "$@" <<'PY'
import functools
import json
import re
import sys

source, entry_path, output, base, channel = sys.argv[1:]
pattern = re.compile(r'([0-9]+)\.([0-9]+)\.([0-9]+)(?:-([0-9A-Za-z.]+))?')
def version_parts(version):
    match = pattern.fullmatch(version)
    if not match:
        raise ValueError(f'Invalid manifest version: {version}')
    return tuple(map(int, match.group(1, 2, 3))), match.group(4)

def compare(left, right):
    a, ap = version_parts(left['version'])
    b, bp = version_parts(right['version'])
    if a != b:
        return (a > b) - (a < b)
    if ap is None or bp is None:
        return (ap is None) - (bp is None)
    for x, y in zip(ap.split('.'), bp.split('.')):
        if x == y:
            continue
        if x.isdigit() and y.isdigit():
            if int(x) == int(y):
                continue
            return (int(x) > int(y)) - (int(x) < int(y))
        if x.isdigit() != y.isdigit():
            return -1 if x.isdigit() else 1
        return (x > y) - (x < y)
    return (len(ap.split('.')) > len(bp.split('.'))) - (len(ap.split('.')) < len(bp.split('.')))

with open(source) as stream:
    manifest = json.load(stream)
if manifest.get('channel', channel) != channel:
    raise ValueError('Manifest channel does not match')
with open(entry_path) as stream:
    entry = json.load(stream)
version_parts(entry['version'])
if entry['file'] != f"printpi-{entry['version']}.tar.gz":
    raise ValueError('Unexpected release filename')
entry['url'] = f"{base}/{channel}/{entry.pop('file')}"
releases = [item for item in manifest.get('releases', []) if item['version'] != entry['version']]
releases.append(entry)
releases.sort(key=functools.cmp_to_key(compare), reverse=True)
with open(output, 'w') as stream:
    json.dump(dict(channel=channel, latest=releases[0]['version'], releases=releases), stream, indent=2)
    stream.write('\n')
PY
}

# Local JSON verification without a network request or upload.
if [[ "${1:-}" == --merge-only ]]; then
    [[ $# == 5 && ( "$2" == stable || "$2" == beta ) ]] || { echo "usage: publish.sh --merge-only CHANNEL MANIFEST ENTRY OUTPUT" >&2; exit 2; }
    merge_manifest "$3" "$4" "$5" "$PRINTPI_UPDATE_URL" "$2"
    exit
fi
[[ $# -ge 1 && $# -le 2 && ( "$1" == stable || "$1" == beta ) ]] || { echo "usage: publish.sh stable|beta [version]" >&2; exit 2; }
CHANNEL="$1"
VERSION="${2:-$(cat "$ROOT/VERSION")}"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] || { echo "invalid version" >&2; exit 2; }
for suffix in tar.gz tar.gz.minisig json; do
    [[ -f "$ROOT/dist/printpi-$VERSION.$suffix" ]] || { echo "Missing dist/printpi-$VERSION.$suffix; run scripts/release.sh first." >&2; exit 1; }
done
[[ "$PRINTPI_UPDATE_URL" =~ ^https://[^[:space:]]+$ ]] || { echo "PRINTPI_UPDATE_URL must use HTTPS" >&2; exit 2; }
[[ "$PRINTPI_UPDATE_SERVER" =~ ^([a-zA-Z0-9_.-]+@)?[a-zA-Z0-9_.-]+:/[a-zA-Z0-9_./-]+$ && "$PRINTPI_UPDATE_SERVER" != -* ]] || { echo "Invalid PRINTPI_UPDATE_SERVER (expected user@host:/path)" >&2; exit 2; }
TEMP="$(mktemp -d "$ROOT/dist/.publish.XXXXXX")"
trap 'rm -rf "$TEMP"' EXIT
MANIFEST_URL="$PRINTPI_UPDATE_URL/$CHANNEL/releases.json"
HTTP_CODE="$(curl -sSL --proto '=https' --proto-redir '=https' --max-time 60 -w '%{http_code}' -o "$TEMP/current.json" "$MANIFEST_URL")"
case "$HTTP_CODE" in
    200) ;;
    404) printf '{"releases":[]}\n' > "$TEMP/current.json" ;;
    *) echo "Cannot fetch manifest: HTTP $HTTP_CODE" >&2; exit 1 ;;
esac
merge_manifest "$TEMP/current.json" "$ROOT/dist/printpi-$VERSION.json" "$TEMP/releases.json" "$PRINTPI_UPDATE_URL" "$CHANNEL"
SSH=(ssh)
RSYNC_SSH=ssh
if [[ -n "$PRINTPI_SSH_KEY" ]]; then
    SSH+=(-i "$PRINTPI_SSH_KEY")
    # rsync parses its remote shell itself; double quotes preserve spaces in key paths.
    escaped_key="${PRINTPI_SSH_KEY//\\/\\\\}"
    escaped_key="${escaped_key//\"/\\\"}"
    RSYNC_SSH="ssh -i \"$escaped_key\""
fi
HOST="${PRINTPI_UPDATE_SERVER%%:*}"
REMOTE_DIR="${PRINTPI_UPDATE_SERVER#*:}/$CHANNEL"
"${SSH[@]}" "$HOST" "mkdir -p '$REMOTE_DIR' && chmod 755 '$REMOTE_DIR'"
# The web server on the VPS runs as its own user, so the files go up world-readable
# (macOS rsync has no --chmod, hence the local chmod).
chmod 644 "$ROOT/dist/printpi-$VERSION.tar.gz" "$ROOT/dist/printpi-$VERSION.tar.gz.minisig" "$TEMP/releases.json"
rsync -az -e "$RSYNC_SSH" "$ROOT/dist/printpi-$VERSION.tar.gz" \
    "$ROOT/dist/printpi-$VERSION.tar.gz.minisig" "$HOST:$REMOTE_DIR/"
# Publish the manifest last, once both downloadable files are present.
rsync -az -e "$RSYNC_SSH" "$TEMP/releases.json" "$HOST:$REMOTE_DIR/"
printf '%s\n' "$MANIFEST_URL"
