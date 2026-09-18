# Building and publishing updates

On the Mac, install minisign and have Node/npm, PHP/Composer, Python 3,
rsync and SSH available. From the repository root, create the signing key once:

```sh
mkdir -p ~/.minisign
minisign -G -p deploy/update.pub -s ~/.minisign/printpi.key
```

Commit only `deploy/update.pub`. Keep the private key and its password safe;
never publish the private key. Deploy the public key to existing Pis with
`scripts/deploy.sh` before offering their first UI update. The installer copies
it to `/etc/printpi/update.pub`.

A GitHub release carries the same tarball and signature; the one-line installer the README
points to is `deploy/get-printpi.sh` on `main` and fetches the newest release by itself.

Publishing a GitHub release also starts `.github/workflows/image.yml`, which downloads the
tarball, checks its signature and runs `scripts/build-image.sh` on an arm64 runner: the official
Raspberry Pi OS Lite image gets its root partition grown, the release unpacked under
`/opt/printpi/releases/<version>` and `deploy/install.sh` run in a chroot with
`PRINTPI_IMAGE_BUILD=1` (nothing is started, the app key and the database wait for the first
boot through `printpi-firstboot.service`). The result, `printpi-<version>.img.xz`, is attached
to the release. The same script runs on any Linux box as root; on x86 it needs the aarch64
binfmt handler with the F flag (`docker run --privileged --rm tonistiigi/binfmt --install arm64`).

Set `VERSION` to the release version. An annotated git tag `v<version>` supplies
the release notes; without one the notes are empty. Build and sign:

```sh
scripts/release.sh
# Optional overrides:
PRINTPI_SIGNING_KEY=~/.minisign/printpi.key SKIP_BUILD=1 scripts/release.sh
```

This produces `dist/printpi-<version>.tar.gz`, its `.minisig`, and a `.json`
manifest entry. `SKIP_BUILD=1` reuses the last frontend build. Dirty working
trees produce a warning and their local changes are included.

The VPS needs only a directory served over HTTPS by nginx or Caddy:

```text
/srv/printpi-updates/
  stable/releases.json
  stable/printpi-<version>.tar.gz
  stable/printpi-<version>.tar.gz.minisig
  beta/releases.json
  beta/printpi-<version>.tar.gz
  beta/printpi-<version>.tar.gz.minisig
```

Allow the SSH user to create these directories and write files. The web server
must be able to traverse the parent directories and read the files. No server
application or database is required. Publish after building:

```sh
scripts/publish.sh stable                 # version defaults to VERSION
scripts/publish.sh beta 0.2.0-beta.1
PRINTPI_UPDATE_SERVER=deploy@vps.example.com:/srv/printpi-updates \
PRINTPI_UPDATE_URL=https://updates.194-164-58-152.sslip.io \
PRINTPI_SSH_KEY=~/.ssh/id_updates scripts/publish.sh stable
```

Defaults are `root@194.164.58.152:/srv/printpi-updates` and
`https://updates.194-164-58-152.sslip.io`. Publishing merges the existing channel
manifest and uploads it after the archive and signature. Serialize publishes
per channel to avoid concurrent manifest edits. Never rebuild a published
version: increment `VERSION`; installed releases are immutable.

The web app offers only the channels listed in `update_channels` in
`app/config/printpi.php` (the first is the default). Only `beta` is listed until
the first stable release: add `stable` there in the release that first ships
on that channel, and the settings page shows the channel select from then on.
