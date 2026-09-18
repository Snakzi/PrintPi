#!/usr/bin/env bash
# Builds a flashable Raspberry Pi OS image with PrintPi already installed.
#
#   sudo scripts/build-image.sh                 dist/printpi-<VERSION>.tar.gz -> dist/printpi-<VERSION>.img.xz
#   PRINTPI_RELEASE=path.tar.gz sudo scripts/build-image.sh
#
# Takes the official Raspberry Pi OS Lite (64-bit) image, grows its root partition, mounts it,
# unpacks the release under /opt/printpi/releases/<version> and runs the release's own
# deploy/install.sh inside a chroot with PRINTPI_IMAGE_BUILD=1, which installs packages, the
# daemon's venv, nginx and the units but starts nothing. The daemon runs as the system user
# printpi-daemon; "printpi" stays free for the login user people create in the Imager. What
# needs a running system (the app key, the database, the plugin list) happens on the first boot
# through printpi-firstboot.
# The boot partition is left alone, so the Raspberry Pi Imager's settings (user, Wi-Fi,
# hostname, SSH) keep working through cloud-init, and rpi-resize still grows the root
# filesystem to the card.
#
# Next to the image an entry for the Raspberry Pi Imager's OS list is written
# (dist/printpi-<VERSION>.imager.json): a user who adds it as a repository in the Imager's settings
# gets PrintPi in the OS list with the usual customisation (user, Wi-Fi, SSH), which the Imager
# does not offer for a local image file.
#
# Needs root on Linux with curl, xz, parted, losetup, e2fsprogs and tar; on a machine that
# is not arm64 also a binfmt handler for aarch64 with the F flag
# (docker run --privileged --rm tonistiigi/binfmt --install arm64).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${PRINTPI_VERSION:-$(cat "$ROOT/VERSION")}"
RELEASE="${PRINTPI_RELEASE:-$ROOT/dist/printpi-$VERSION.tar.gz}"
BASE_IMAGE_URL="${PRINTPI_BASE_IMAGE_URL:-https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2026-09-15/2026-09-15-raspios-trixie-arm64-lite.img.xz}"
WORK="${PRINTPI_IMAGE_WORK:-/var/tmp/printpi-image}"
GROW_MIB="${PRINTPI_IMAGE_GROW:-2560}"
IMAGE_HOSTNAME="${PRINTPI_IMAGE_HOSTNAME:-printpi}"
DAEMON_USER=printpi-daemon
OUT="${PRINTPI_IMAGE_OUT:-$ROOT/dist/printpi-$VERSION.img.xz}"
# Where the image will be downloadable from, for the Imager entry.
IMAGE_URL="${PRINTPI_IMAGE_URL:-https://github.com/Snakzi/PrintPi/releases/download/v$VERSION/$(basename "$OUT")}"
ICON_URL="${PRINTPI_IMAGE_ICON_URL:-https://raw.githubusercontent.com/Snakzi/PrintPi/main/app/public/images/imager-icon.png}"

log() { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m!!\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "run as root"
for tool in curl xz parted losetup e2fsck resize2fs tar chroot; do
    command -v "$tool" >/dev/null || die "$tool is missing"
done
[[ -f "$RELEASE" ]] || die "no release at $RELEASE; build it with scripts/release.sh first"
if [[ "$(uname -m)" != aarch64 ]]; then
    [[ -f /proc/sys/fs/binfmt_misc/qemu-aarch64 ]] || die "no aarch64 emulation on this machine"
    grep -q '^flags:.*F' /proc/sys/fs/binfmt_misc/qemu-aarch64 || die "the aarch64 binfmt handler needs the F flag"
fi

mkdir -p "$WORK/base" "$(dirname "$OUT")"
BASE_XZ="$WORK/base/$(basename "$BASE_IMAGE_URL")"
if [[ ! -f "$BASE_XZ" ]]; then
    log "Downloading $(basename "$BASE_IMAGE_URL")"
    curl -fL --progress-bar -o "$BASE_XZ" "$BASE_IMAGE_URL"
fi

IMG="$WORK/printpi-$VERSION.img"
MNT="$WORK/root"
LOOP=""
cleanup() {
    set +e
    for mountpoint in "$MNT/boot/firmware" "$MNT/run" "$MNT/tmp" "$MNT/sys" "$MNT/proc" "$MNT/dev/pts" "$MNT/dev" "$MNT"; do
        mountpoint -q "$mountpoint" && umount -l "$mountpoint"
    done
    [[ -n "$LOOP" ]] && losetup -d "$LOOP"
}
trap cleanup EXIT

log "Unpacking the base image"
xz -dc "$BASE_XZ" > "$IMG"
log "Growing the root partition by $GROW_MIB MiB"
truncate -s +"${GROW_MIB}M" "$IMG"
parted -s "$IMG" resizepart 2 100%
LOOP="$(losetup -fP --show "$IMG")"
e2fsck -fp "${LOOP}p2" >/dev/null
resize2fs "${LOOP}p2" >/dev/null 2>&1

log "Mounting"
mkdir -p "$MNT"
mount "${LOOP}p2" "$MNT"
mount "${LOOP}p1" "$MNT/boot/firmware"
mount --bind /dev "$MNT/dev"
mount --bind /dev/pts "$MNT/dev/pts"
mount -t proc proc "$MNT/proc"
mount -t sysfs sysfs "$MNT/sys"
mount -t tmpfs tmpfs "$MNT/tmp"
mount -t tmpfs tmpfs "$MNT/run"
cp -a "$MNT/etc/resolv.conf" "$WORK/resolv.conf.image"
cp -L /etc/resolv.conf "$MNT/etc/resolv.conf"
# Package installs must not start services inside the chroot.
printf '#!/bin/sh\nexit 101\n' > "$MNT/usr/sbin/policy-rc.d"
chmod 755 "$MNT/usr/sbin/policy-rc.d"

log "Unpacking PrintPi $VERSION"
TARGET="$MNT/opt/printpi/releases/$VERSION"
mkdir -p "$TARGET"
tar -xzf "$RELEASE" -C "$TARGET" --strip-components=1 --no-same-owner --no-same-permissions
[[ "$(cat "$TARGET/VERSION")" == "$VERSION" ]] || die "the release archive is not $VERSION"

log "Preparing the system"
echo "$IMAGE_HOSTNAME" > "$MNT/etc/hostname"
sed -i "s/\braspberrypi\b/$IMAGE_HOSTNAME/" "$MNT/etc/hosts"
# SPI for the LED strip plugin on pins 10 and 20, the pins that work on every Pi.
grep -q '^dtparam=spi=on' "$MNT/boot/firmware/config.txt" || printf '\n# PrintPi: SPI for the LED strip plugin\ndtparam=spi=on\n' >> "$MNT/boot/firmware/config.txt"
if ! chroot "$MNT" getent passwd "$DAEMON_USER" >/dev/null; then
    chroot "$MNT" useradd --system --home-dir /var/lib/printpi --no-create-home --shell /usr/sbin/nologin "$DAEMON_USER"
fi

log "Installing PrintPi in the chroot"
chroot "$MNT" env PRINTPI_IMAGE_BUILD=1 PRINTPI_USER="$DAEMON_USER" PRINTPI_HOME=/opt/printpi DEBIAN_FRONTEND=noninteractive \
    bash "/opt/printpi/releases/$VERSION/deploy/install.sh"

log "Cleaning up"
chroot "$MNT" apt-get clean
rm -rf "$MNT/var/lib/apt/lists/"* "$MNT/var/lib/printpi/.cache" "$MNT/root/.cache" "$MNT/usr/sbin/policy-rc.d"
cp -a "$WORK/resolv.conf.image" "$MNT/etc/resolv.conf"
# Zeroed free space compresses to nothing.
dd if=/dev/zero of="$MNT/printpi-zero" bs=1M status=none 2>/dev/null || true
rm -f "$MNT/printpi-zero"
sync
df -h "$MNT" | tail -n 1
cleanup
trap - EXIT
LOOP=""

log "Compressing to $OUT"
RAW_SIZE="$(stat -c %s "$IMG")"
RAW_SHA256="$(sha256sum "$IMG" | cut -d' ' -f1)"
xz -T0 -6 -c "$IMG" > "$OUT"
rm -f "$IMG"
(cd "$(dirname "$OUT")" && sha256sum "$(basename "$OUT")" > "$(basename "$OUT").sha256")
ls -la "$OUT"

log "Writing the Imager entry"
python3 - "$OUT" "$VERSION" "$IMAGE_URL" "$ICON_URL" "$RAW_SIZE" "$RAW_SHA256" <<'PY'
import datetime, hashlib, json, os, sys
out, version, url, icon, raw_size, raw_sha256 = sys.argv[1:]
digest = hashlib.sha256()
with open(out, "rb") as handle:
    for chunk in iter(lambda: handle.read(1 << 20), b""):
        digest.update(chunk)
entry = {
    "name": f"PrintPi {version}",
    "description": "Raspberry Pi OS Lite (64-bit) with PrintPi installed: the print server for Marlin printers over USB",
    "icon": icon,
    "url": url,
    "extract_size": int(raw_size),
    "extract_sha256": raw_sha256,
    "image_download_size": os.path.getsize(out),
    "image_download_sha256": digest.hexdigest(),
    "release_date": datetime.date.today().isoformat(),
    "init_format": "cloudinit-rpi",
    "devices": ["pi5-64bit", "pi4-64bit", "pi3-64bit"],
    "capabilities": [],
}
target = out.removesuffix(".img.xz") + ".imager.json"
with open(target, "w") as handle:
    json.dump({"os_list": [entry]}, handle, indent=2)
    handle.write("\n")
print(target)
PY
log "Done: flash $OUT with the Raspberry Pi Imager, set user, Wi-Fi and SSH there, boot, open http://$IMAGE_HOSTNAME.local"
