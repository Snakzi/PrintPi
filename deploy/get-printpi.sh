#!/usr/bin/env bash
# Installs the newest PrintPi release on a Raspberry Pi:
#
#   curl -fsSL https://raw.githubusercontent.com/Snakzi/PrintPi/main/deploy/get-printpi.sh | sudo bash
#
# A version can be pinned with `sudo bash -s 0.2.0-beta.22`. The release is unpacked under
# /opt/printpi/releases/<version>, its signature checked, and its own installer run; from
# then on the settings page updates PrintPi.
set -euo pipefail

REPO="Snakzi/PrintPi"
PRINTPI_HOME="${PRINTPI_HOME:-/opt/printpi}"
# deploy/update.pub of the repository; every release is signed with its private key.
PUBLIC_KEY="RWQS7xq+WMBY0GlDwBjIq7hTvGc0rzVQDyFF6XJ1l5cu56hRWdgVExfy"

[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
command -v curl >/dev/null || { echo "curl is missing" >&2; exit 1; }

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
    VERSION="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
        | sed -n 's/.*"tag_name": *"v\([^"]*\)".*/\1/p' | head -n 1)"
    [[ -n "$VERSION" ]] || { echo "could not find the latest release of $REPO" >&2; exit 1; }
fi
TARGET="$PRINTPI_HOME/releases/$VERSION"

if [[ "$(cat "$TARGET/VERSION" 2>/dev/null)" == "$VERSION" ]]; then
    echo "==> PrintPi $VERSION is already unpacked"
else
    URL="https://github.com/$REPO/releases/download/v$VERSION/printpi-$VERSION.tar.gz"
    WORK="$(mktemp -d)"
    trap 'rm -rf "$WORK"' EXIT
    echo "==> Downloading PrintPi $VERSION"
    curl -fsSL -o "$WORK/printpi.tar.gz" "$URL"
    curl -fsSL -o "$WORK/printpi.tar.gz.minisig" "$URL.minisig"
    if ! command -v minisign >/dev/null; then
        apt-get install -y -qq minisign >/dev/null 2>&1 || { apt-get update -qq && apt-get install -y -qq minisign >/dev/null; }
    fi
    echo "==> Checking the signature"
    minisign -Vqm "$WORK/printpi.tar.gz" -P "$PUBLIC_KEY" || { echo "the signature of $URL does not check out" >&2; exit 1; }
    mkdir -p "$TARGET"
    tar -xzf "$WORK/printpi.tar.gz" -C "$TARGET" --strip-components=1 --no-same-owner --no-same-permissions
fi

exec bash "$TARGET/deploy/install.sh"
